#!/usr/bin/env bash

# ================================
# Анализатор локальных профилей
# ================================

# Проверка версии bash
if (( BASH_VERSINFO[0] < 5 )); then
    echo "Ошибка: требуется bash версии 5.0 или выше"
    exit 1
fi

# Цвета ANSI
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
CYAN="\033[36m"
RESET="\033[0m"

info()    { echo -e "${BLUE}[INFO]${RESET} $1"; }
success() { echo -e "${GREEN}[OK]${RESET} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET} $1"; }
error()   { echo -e "${RED}[ERROR]${RESET} $1"; }

# ===== ШАГ 1. Ввод логина =====
if [[ -n "$1" ]]; then
    USERNAME="$1"
else
    read -rp "Введите логин пользователя: " USERNAME
fi

if [[ -z "$USERNAME" ]]; then
    error "Логин пользователя не задан"
    exit 1
fi

# ===== ШАГ 2. Проверка существования =====
USER_ENTRY=$(getent passwd "$USERNAME")
if [[ -z "$USER_ENTRY" ]]; then
    error "Пользователь '$USERNAME' не найден"
    exit 1
fi

# ===== ШАГ 3. Разбор passwd и shell =====
IFS=':' read -r LOGIN PASS _ _ GECOS HOME SHELL <<< "$USER_ENTRY"

# Проверка shell
CAN_LOGIN=true
case "$SHELL" in
    /bin/*sh) ;;
    /sbin/nologin|/bin/false|/dev/null|"") CAN_LOGIN=false ;;
    *) CAN_LOGIN=false ;;
esac

# ===== ШАГ 4. Основная информация =====
echo -e "\n${CYAN}=== Основная информация ===${RESET}"
echo -e "Логин:            ${GREEN}$LOGIN${RESET}"

# Правильный UID/GID для выбранного пользователя
UID=$(id -u "$LOGIN")
GID=$(id -g "$LOGIN")

echo -e "UID:              $UID"
echo -e "GID:              $GID"
echo -e "Полное имя:       ${GECOS:-Не указано}"
echo -e "Домашний каталог: $HOME"
echo -e "Shell:            $SHELL"

if $CAN_LOGIN; then
    success "Интерактивный вход разрешён"
else
    warn "Интерактивный вход запрещён"
fi

# Группы
GROUPS_LIST=$(id -nG "$LOGIN" 2>/dev/null)
echo -e "Группы:           ${GROUPS_LIST:-Не удалось получить}"

# Статус блокировки
LOCK_STATUS=$(passwd -S "$LOGIN" 2>/dev/null | awk '{print $2}')
if [[ "$LOCK_STATUS" == "L" ]]; then
    echo -e "Статус:           ${RED}ЗАБЛОКИРОВАН${RESET}"
else
    echo -e "Статус:           ${GREEN}АКТИВЕН${RESET}"
fi

# ===== ШАГ 5. Последний вход =====
echo -e "\n${CYAN}=== Последний вход ===${RESET}"

# Используем last вместо lastlog для корректного отображения
LAST_ENTRY=$(last -F "$LOGIN" 2>/dev/null | grep -v "wtmp begins" | head -n 1)
if [[ -z "$LAST_ENTRY" ]]; then
    warn "Пользователь ни разу не входил в систему"
else
    echo "$LAST_ENTRY"
fi

# ===== ШАГ 6. Размер home =====
echo -e "\n${CYAN}=== Домашний каталог ===${RESET}"
if [[ -d "$HOME" ]]; then
    du -sh "$HOME" 2>/dev/null || warn "Нет доступа"
else
    warn "Домашняя директория не существует"
fi

# ===== ШАГ 7. ТОП-10 файлов =====
echo -e "\n${CYAN}=== ТОП-10 самых больших файлов ===${RESET}"
find "$HOME" -type f -exec du -h {} + 2>/dev/null | sort -hr | head -10 || warn "Файлы не найдены"

# ===== ШАГ 8. Чужие файлы =====
echo -e "\n${CYAN}=== Файлы не владельца ===${RESET}"
FOREIGN=$(find "$HOME" -type f ! -user "$LOGIN" -exec stat -c "%U %n" {} \; 2>/dev/null)
if [[ -n "$FOREIGN" ]]; then
    echo "$FOREIGN"
else
    success "Все файлы принадлежат пользователю"
fi

# ===== ШАГ 9. ТОП-5 команд =====
echo -e "\n${CYAN}=== ТОП-5 команд ===${RESET}"
HIST="$HOME/.bash_history"
if [[ -f "$HIST" ]]; then
    awk '{print $1}' "$HIST" | sort | uniq -c | sort -nr | head -5
else
    warn ".bash_history не найден"
fi

# ===== ШАГ 10. ТОП-5 процессов =====
echo -e "\n${CYAN}=== ТОП-5 процессов по памяти ===${RESET}"
ps -u "$LOGIN" -o pid,comm,%mem,%cpu --sort=-%mem 2>/dev/null | head -6 || warn "Процессы не найдены"

echo -e "\n${GREEN}Анализ пользователя '$LOGIN' завершён${RESET}"
exit 0
