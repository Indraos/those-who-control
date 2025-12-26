#!/usr/bin/env bash
# ==============================================================
# 💾 OLD MS-DOS BLUE TERMINAL THEME
# Blue background, gray text, green prompt, blinking block cursor
#
# Activate:  source terminal-theme.sh && oldschool_on
# Revert:    oldschool_off
# ==============================================================

if [ -z "${OLDSCHOOL_SAVED+x}" ]; then
  export OLDSCHOOL_SAVED=1
  export OLDSCHOOL_PREV_PS1="${PS1-}"
  export OLDSCHOOL_PREV_PROMPT="${PROMPT-}"
  export OLDSCHOOL_PREV_RPROMPT="${RPROMPT-}"
  export OLDSCHOOL_PREV_TERM="${TERM-}"
fi

# --------------------------------------------------------------
# Color helpers
# --------------------------------------------------------------
set_dos_colors() {
  # 0 = reset, 37 = light gray fg, 44 = blue bg
  printf '\033[0;37;44m'
}

reset_colors() {
  printf '\033[0m'
}

# --------------------------------------------------------------
# Cursor helpers
# --------------------------------------------------------------
enable_blinking_block_cursor() {
  # 12h = blinking, 112c = block
  printf '\e[?12h\e[?112c'
}

disable_blinking_block_cursor() {
  printf '\e[?12l\e[?0c'
}

# --------------------------------------------------------------
# Prompt control
# --------------------------------------------------------------
oldschool_on() {
  set_dos_colors
  enable_blinking_block_cursor

  # Green prompt text on blue background
  local green='\[\e[0;32m\]'
  local reset='\[\e[0m\]'

  if [ -n "${ZSH_VERSION-}" ]; then
    PROMPT='%F{green}have you changed?%f '
    RPROMPT=''
  else
    PS1="${green}have you changed? ${reset}"
  fi

  # Disable modern color aliases
  unalias ls 2>/dev/null || true
  unalias grep 2>/dev/null || true
  alias ls='ls --color=never' 2>/dev/null || true
  alias grep='grep --color=never' 2>/dev/null || true
  export CLICOLOR=0
  unset LSCOLORS || true

  # Optional: VT100-like term
  if command -v tput >/dev/null 2>&1; then
    export TERM="vt100"
  fi
}

oldschool_off() {
  reset_colors
  disable_blinking_block_cursor

  if [ -n "${ZSH_VERSION-}" ]; then
    PROMPT="${OLDSCHOOL_PREV_PROMPT-}"
    RPROMPT="${OLDSCHOOL_PREV_RPROMPT-}"
  else
    PS1="${OLDSCHOOL_PREV_PS1-}"
  fi

  if [ -n "${OLDSCHOOL_PREV_TERM-}" ]; then
    export TERM="${OLDSCHOOL_PREV_TERM}"
  fi
}

# --------------------------------------------------------------
# Optional autostart
# --------------------------------------------------------------
# oldschool_on