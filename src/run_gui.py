import tkinter as tk

from fc2_gui.gui import FC2MagnetGUI


def main() -> None:
    root = tk.Tk()
    FC2MagnetGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

