import tkinter as tk
from tkinter import messagebox
import random
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, List

SAVE_FILE = "fazendinha_gui_save.json"
TICK_INTERVAL = 1.0  # segundos por tick

# ---------- Definições de culturas ----------
@dataclass
class CropType:
    name: str
    grow_time: int
    sell_price: int
    water_need: int
    seed_price: int

CROP_TYPES = {
    "cenoura": CropType("Cenoura", grow_time=8, sell_price=15, water_need=2, seed_price=5),
    "milho":   CropType("Milho", grow_time=14, sell_price=35, water_need=4, seed_price=12),
    "batata":  CropType("Batata", grow_time=10, sell_price=22, water_need=3, seed_price=8),
}

# ---------- Campo ----------
@dataclass
class Plot:
    crop: Optional[str] = None
    age: int = 0
    water: int = 0
    infected: bool = False

    def is_empty(self):
        return self.crop is None

    def ready_to_harvest(self):
        if not self.crop:
            return False
        c = CROP_TYPES[self.crop]
        return self.age >= c.grow_time and self.water >= c.water_need and not (self.infected and random.random() < 0.4)

# ---------- Fazenda ----------
@dataclass
class Farm:
    rows: int = 5
    cols: int = 5
    plots: List[Plot] = field(default_factory=list)
    coins: int = 50
    autos: dict = field(default_factory=lambda: {"regador": False, "plantador": False, "colhedor": False})
    upgrades: dict = field(default_factory=lambda: {"regador_level": 0, "plantador_level": 0, "colhedor_level": 0})
    tick_count: int = 0

    def __post_init__(self):
        if not self.plots:
            self.plots = [Plot() for _ in range(self.rows * self.cols)]

    def to_dict(self):
        return {
            "rows": self.rows,
            "cols": self.cols,
            "plots": [p.__dict__ for p in self.plots],
            "coins": self.coins,
            "autos": self.autos,
            "upgrades": self.upgrades,
            "tick_count": self.tick_count,
        }

    @staticmethod
    def from_dict(d):
        f = Farm(rows=d.get("rows",5), cols=d.get("cols",5))
        f.plots = [Plot(**pd) for pd in d["plots"]]
        f.coins = d["coins"]
        f.autos = d["autos"]
        f.upgrades = d["upgrades"]
        f.tick_count = d["tick_count"]
        return f

# ---------- Funções de jogo ----------
def save_game(farm):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(farm.to_dict(), f, indent=2)

def load_game():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            return Farm.from_dict(d)
        except:
            pass
    return Farm()

# ---------- GUI ----------
class FarmGame:
    def __init__(self, root):
        self.root = root
        self.root.title("🌾 Fazendinha Automatizada")
        self.farm = load_game()

        self.buttons = []
        self.create_ui()

        self.running = True
        self.thread = threading.Thread(target=self.tick_loop, daemon=True)
        self.thread.start()

    def create_ui(self):
        frame_farm = tk.Frame(self.root)
        frame_farm.grid(row=0, column=0, padx=10, pady=10)

        # Cria botões da fazenda
        for i in range(self.farm.rows):
            for j in range(self.farm.cols):
                idx = i * self.farm.cols + j
                btn = tk.Button(frame_farm, width=8, height=3,
                                command=lambda i=idx: self.on_plot_click(i))
                btn.grid(row=i, column=j, padx=2, pady=2)
                self.buttons.append(btn)

        # Painel lateral
        side = tk.Frame(self.root)
        side.grid(row=0, column=1, sticky="ns", padx=10)

        self.label_info = tk.Label(side, text="", justify="left", font=("Arial", 12))
        self.label_info.pack(pady=5)

        tk.Button(side, text="🌱 Plantar Cenoura (5c)", command=lambda: self.plant_mode("cenoura")).pack(fill="x")
        tk.Button(side, text="🌽 Plantar Milho (12c)", command=lambda: self.plant_mode("milho")).pack(fill="x")
        tk.Button(side, text="🥔 Plantar Batata (8c)", command=lambda: self.plant_mode("batata")).pack(fill="x")
        tk.Button(side, text="💧 Regar Tudo", command=self.water_all).pack(fill="x")
        tk.Button(side, text="🧺 Colher Tudo", command=self.harvest_all).pack(fill="x")
        tk.Button(side, text="🛒 Loja", command=self.shop_menu).pack(fill="x")
        tk.Button(side, text="💾 Salvar", command=lambda: save_game(self.farm)).pack(fill="x")
        tk.Button(side, text="🚪 Sair", command=self.exit_game).pack(fill="x")

        self.update_ui()

    def plant_mode(self, crop_key):
        self.selected_crop = crop_key
        messagebox.showinfo("Modo Plantio", f"Selecione um terreno para plantar {crop_key.capitalize()}.")

    def on_plot_click(self, idx):
        plot = self.farm.plots[idx]
        if hasattr(self, "selected_crop") and self.selected_crop:
            self.plant_crop(idx, self.selected_crop)
            self.selected_crop = None
        elif not plot.is_empty():
            if plot.ready_to_harvest():
                self.harvest_plot(idx)
            else:
                plot.water += 1
        self.update_ui()

    def plant_crop(self, idx, crop_key):
        plot = self.farm.plots[idx]
        if not plot.is_empty():
            messagebox.showinfo("Aviso", "Este terreno já está ocupado.")
            return
        price = CROP_TYPES[crop_key].seed_price
        if self.farm.coins < price:
            messagebox.showinfo("Sem Coins", "Você não tem dinheiro suficiente.")
            return
        self.farm.coins -= price
        plot.crop = crop_key
        plot.age = 0
        plot.water = 0
        plot.infected = False
        self.update_ui()

    def water_all(self):
        for p in self.farm.plots:
            if not p.is_empty():
                p.water += 1
        self.update_ui()

    def harvest_all(self):
        harvested = 0
        for i, p in enumerate(self.farm.plots):
            if p.ready_to_harvest():
                self.harvest_plot(i)
                harvested += 1
        if harvested == 0:
            messagebox.showinfo("Nada para colher", "Nenhuma planta está pronta ainda.")
        self.update_ui()

    def harvest_plot(self, idx):
        plot = self.farm.plots[idx]
        if not plot.ready_to_harvest():
            return
        crop = CROP_TYPES[plot.crop]
        gain = crop.sell_price
        self.farm.coins += gain
        plot.crop = None
        plot.age = 0
        plot.water = 0
        plot.infected = False

    def shop_menu(self):
        shop = tk.Toplevel(self.root)
        shop.title("🛒 Loja da Fazenda")

        tk.Label(shop, text="Bem-vindo à Loja!", font=("Arial", 14, "bold")).pack(pady=5)
        tk.Label(shop, text=f"Coins atuais: {self.farm.coins}").pack(pady=5)

        def buy_auto(name, cost):
            if self.farm.coins >= cost:
                self.farm.coins -= cost
                self.farm.autos[name] = True
                messagebox.showinfo("Comprado", f"{name.capitalize()} automático ativado!")
                self.update_ui()
            else:
                messagebox.showinfo("Sem coins", "Dinheiro insuficiente.")

        tk.Button(shop, text="💧 Regador Automático (100c)", command=lambda: buy_auto("regador", 100)).pack(fill="x", pady=3)
        tk.Button(shop, text="🌱 Plantador Automático (150c)", command=lambda: buy_auto("plantador", 150)).pack(fill="x", pady=3)
        tk.Button(shop, text="🧺 Colhedor Automático (200c)", command=lambda: buy_auto("colhedor", 200)).pack(fill="x", pady=3)
        tk.Button(shop, text="Fechar", command=shop.destroy).pack(pady=5)

    def tick_loop(self):
        while self.running:
            time.sleep(TICK_INTERVAL)
            self.farm.tick_count += 1
            for p in self.farm.plots:
                if not p.is_empty():
                    p.age += 1
                    if random.random() < 0.01:
                        p.infected = True
            self.do_automation_tick()
            save_game(self.farm)
            self.root.after(0, self.update_ui)

    def do_automation_tick(self):
        if self.farm.autos["regador"]:
            for p in self.farm.plots:
                if not p.is_empty():
                    p.water += 1

        if self.farm.autos["plantador"]:
            for p in self.farm.plots:
                if p.is_empty() and self.farm.coins >= 5:
                    self.plant_crop(self.farm.plots.index(p), "cenoura")

        if self.farm.autos["colhedor"]:
            for i, p in enumerate(self.farm.plots):
                if p.ready_to_harvest():
                    self.harvest_plot(i)

    def update_ui(self):
        for i, p in enumerate(self.farm.plots):
            btn = self.buttons[i]
            if p.is_empty():
                btn.config(text="🌾", bg="lightgreen")
            else:
                crop = CROP_TYPES[p.crop]
                if p.ready_to_harvest():
                    btn.config(text=f"{crop.name}\n✅", bg="gold")
                elif p.infected:
                    btn.config(text=f"{crop.name}\n💀", bg="red")
                else:
                    growth = int((p.age / crop.grow_time) * 100)
                    growth = min(growth, 100)
                    btn.config(text=f"{crop.name}\n{growth}%", bg="lightyellow")

        info = (
            f"💰 Coins: {self.farm.coins}\n"
            f"⏱️ Ticks: {self.farm.tick_count}\n\n"
            f"Autos:\n"
            f"  💧 Regador: {self.farm.autos['regador']}\n"
            f"  🌱 Plantador: {self.farm.autos['plantador']}\n"
            f"  🧺 Colhedor: {self.farm.autos['colhedor']}"
        )
        self.label_info.config(text=info)

    def exit_game(self):
        save_game(self.farm)
        self.running = False
        self.root.destroy()

# ---------- Main ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = FarmGame(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_game)
    root.mainloop()
