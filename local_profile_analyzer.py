#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import shlex
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
from datetime import datetime

class UserAnalyzer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Анализатор локальных профилей | Мостех Linux")
        self.geometry("1000x780")
        self.configure(bg="#1e1e1e")
        self._build_gui()

    def _build_gui(self):
        heart = r"""

      —̳͟͞͞💗
 —̳͟͞͞ 💗         —̳͟͞͞💗  
         —̳͟͞͞💗
  —̳͟͞͞💗         —̳͟͞͞💗 



"""
        splash = tk.Label(self, text=heart, font=("Courier", 11), fg="#ff5f87", bg="#1e1e1e")
        splash.pack(pady=8)

        top = tk.Frame(self, bg="#1e1e1e")
        top.pack(pady=5)

        tk.Label(top, text="Логин пользователя:", fg="white", bg="#1e1e1e").pack(side=tk.LEFT)
        self.user_entry = tk.Entry(top, width=30)
        self.user_entry.pack(side=tk.LEFT, padx=10)
        tk.Button(top, text="Анализировать", command=self.analyze_user).pack(side=tk.LEFT)
        tk.Button(top, text="Очистить отчёт", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="Сохранить отчёт (TXT)", command=self.save_report).pack(side=tk.LEFT, padx=5)

        self.output = scrolledtext.ScrolledText(self, bg="#111111", fg="#00ff9c",
                                                insertbackground="white",
                                                font=("Courier", 10))
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.write("Готово к работе. Введите логин пользователя.\n")

    def write(self, text=""):
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)

    def clear_output(self):
        if messagebox.askyesno("Очистка", "Очистить весь отчёт?"):
            self.output.delete(1.0, tk.END)

    def save_report(self):
        content = self.output.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Сохранение", "Отчёт пуст")
            return
        default_name = f"user_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 initialfile=default_name,
                                                 filetypes=[("Text files", "*.txt")])
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Сохранение", f"Отчёт сохранён:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def analyze_user(self):
        username = self.user_entry.get().strip()
        if not username:
            messagebox.showerror("Ошибка", "Введите логин пользователя")
            return

        self.write("="*80)
        self.write(f"Анализ пользователя: {username}")
        self.write(f"Дата и время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.write("="*80)

        try:
            user_entry = subprocess.getoutput(f"getent passwd {shlex.quote(username)}")
            if not user_entry:
                self.write(f"[ERROR] Пользователь {username} не найден")
                return

            # Безопасный разбор passwd
            parts = user_entry.strip().split(":")
            LOGIN = parts[0] if len(parts) > 0 else username
            PASSWD = parts[1] if len(parts) > 1 else ""
            UID = parts[2] if len(parts) > 2 else "0"
            GID = parts[3] if len(parts) > 3 else "0"
            GECOS = parts[4] if len(parts) > 4 and parts[4] else "Не указано"
            HOME = parts[5] if len(parts) > 5 and parts[5] else f"/home/{LOGIN}"
            SHELL = parts[6] if len(parts) > 6 and parts[6] else "/bin/bash"

            can_login = SHELL.startswith("/bin/") and SHELL.endswith("sh") and SHELL not in ("/sbin/nologin","/bin/false","/dev/null")

            # UID/GID/Groups
            uid = subprocess.getoutput(f"id -u {LOGIN}")
            gid = subprocess.getoutput(f"id -g {LOGIN}")
            groups = subprocess.getoutput(f"id -nG {LOGIN}")

            # Статус блокировки
            lock_output = subprocess.getoutput(f"passwd -S {LOGIN} 2>/dev/null").split()
            lock_status = lock_output[1] if len(lock_output) > 1 else "?"
            status = "ЗАБЛОКИРОВАН" if lock_status=="L" else "АКТИВЕН"

            self.write("\n[ ОСНОВНАЯ ИНФОРМАЦИЯ ]")
            self.write(f"Логин: {LOGIN}")
            self.write(f"UID: {uid}")
            self.write(f"GID: {gid}")
            self.write(f"GECOS: {GECOS}")
            self.write(f"HOME: {HOME}")
            self.write(f"Shell: {SHELL}")
            self.write(f"Группы: {groups if groups else '[INFO] Не удалось получить'}")
            self.write(f"Статус: {status}")
            self.write(f"{'[INFO] Интерактивный вход разрешён' if can_login else '[WARN] Вход запрещён'}")

            # Последний вход
            proc_last = subprocess.run(["last", "-F", LOGIN], capture_output=True, text=True)
            lines = [l for l in proc_last.stdout.splitlines() if "wtmp begins" not in l]
            last_entry = lines[0] if lines else "[WARN] Пользователь ни разу не входил в систему"
            self.write("\n[ ПОСЛЕДНИЙ ВХОД ]")
            self.write(last_entry)

            # Размер HOME
            proc_du = subprocess.run(["du","-sh", HOME], capture_output=True, text=True)
            du_out = proc_du.stdout.strip() if proc_du.returncode == 0 else "[WARN] Недоступно"
            self.write("\n[ СУММАРНЫЙ РАЗМЕР HOME ]")
            self.write(du_out)

            # ТОП-10 файлов
            cmd_top_files = f"find {shlex.quote(HOME)} -type f -exec du -h {{}} + 2>/dev/null | sort -hr | head -10"
            top_files = subprocess.getoutput(cmd_top_files)
            self.write("\n[ ТОП-10 САМЫХ БОЛЬШИХ ФАЙЛОВ ]")
            self.write(top_files if top_files else "[WARN] Файлы не найдены")

            # Чужие файлы
            cmd_foreign = f"find {shlex.quote(HOME)} -type f ! -user {LOGIN} -exec stat -c '%U %n' {{}} \\; 2>/dev/null"
            foreign = subprocess.getoutput(cmd_foreign)
            self.write("\n[ ФАЙЛЫ В HOME НЕ ОТ ПОЛЬЗОВАТЕЛЯ ]")
            self.write(foreign if foreign else "[INFO] Все файлы принадлежат пользователю")

            # ТОП-5 команд
            hist_file = os.path.join(HOME, ".bash_history")
            self.write("\n[ ТОП-5 КОМАНД ]")
            if os.path.isfile(hist_file):
                cmds = subprocess.getoutput(f"awk '{{print $1}}' {shlex.quote(hist_file)} | sort | uniq -c | sort -nr | head -5")
                self.write(cmds if cmds else "[INFO] История пуста")
            else:
                self.write("[WARN] .bash_history не найден")

            # ТОП-5 процессов
            proc_ps = subprocess.run(["ps","-u", LOGIN,"-o","pid,comm,%mem,%cpu","--sort=-%mem"], capture_output=True, text=True)
            ps_out = "\n".join(proc_ps.stdout.splitlines()[:6]) if proc_ps.returncode==0 else "[INFO] Процессы не найдены"
            self.write("\n[ ТОП-5 ПРОЦЕССОВ ПО ПАМЯТИ ]")
            self.write(ps_out)

            self.write(f"\n[OK] Анализ пользователя '{LOGIN}' завершён\n")

        except Exception as e:
            self.write(f"[ERROR] Не удалось выполнить анализ: {e}")

if __name__ == "__main__":
    app = UserAnalyzer()
    app.mainloop()
