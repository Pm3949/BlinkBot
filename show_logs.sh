#!/usr/bin/env bash

# Names of our Docker containers
CONTAINERS=(
    "ragmate-control-plane"
    "ragmate-ai-engine"
    "ragmate-nginx"
    "ragmate-redis"
)

echo "Starting Docker Logs Streamers..."

# Auto-detect installed terminal emulator
LAUNCHED=false

# 1. Primary Fallback: If tmux is available, split the terminal into a 2x2 layout
if command -v tmux &> /dev/null; then
    echo "Detected tmux. Launching 2x2 logs grid..."
    SESSION_NAME="ragmate_logs"
    
    # Kill existing logs session if running
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    
    # Create a new detached session running the first log
    tmux new-session -d -s "$SESSION_NAME" "docker logs -f ragmate-control-plane"
    
    # Split horizontally (creates bottom pane) and run the second log
    tmux split-window -v -t "$SESSION_NAME" "docker logs -f ragmate-ai-engine"
    
    # Split the top pane vertically and run the third log
    tmux split-window -h -t "$SESSION_NAME.0" "docker logs -f ragmate-nginx"
    
    # Split the bottom pane vertically and run the fourth log
    tmux split-window -h -t "$SESSION_NAME.2" "docker logs -f ragmate-redis"
    
    # Select layout grid and attach
    tmux select-layout -t "$SESSION_NAME" tiled
    tmux attach-session -t "$SESSION_NAME"
    LAUNCHED=true
fi

if [ "$LAUNCHED" = false ]; then
    # List of terminal launchers with their command execution flags
    declare -A TERMINALS
    TERMINALS["gnome-terminal"]="--title=\$TITLE -- bash -c"
    TERMINALS["konsole"]="--new-tab -e"
    TERMINALS["xfce4-terminal"]="--title=\$TITLE -e"
    TERMINALS["tilix"]="-t \$TITLE -e"
    TERMINALS["mate-terminal"]="--title=\$TITLE -e"
    TERMINALS["lxterminal"]="--title=\$TITLE -e"
    TERMINALS["kitty"]="--title=\$TITLE"
    TERMINALS["alacritty"]="-t \$TITLE -e"
    TERMINALS["wezterm"]="start --"
    TERMINALS["xterm"]="-T \$TITLE -e"

    for term in "${!TERMINALS[@]}"; do
        if command -v "$term" &> /dev/null; then
            echo "Detected terminal: $term"
            for container in "${CONTAINERS[@]}"; do
                TITLE="$container Logs"
                case "$term" in
                    "gnome-terminal")
                        gnome-terminal --title="$TITLE" -- bash -c "docker logs -f $container; exec bash" &
                        ;;
                    "konsole")
                        konsole --new-tab -e "docker logs -f $container" &
                        ;;
                    "xfce4-terminal"|"mate-terminal"|"lxterminal")
                        "$term" --title="$TITLE" -e "docker logs -f $container" &
                        ;;
                    "tilix")
                        tilix -t "$TITLE" -e "docker logs -f $container" &
                        ;;
                    "kitty")
                        kitty --title "$TITLE" sh -c "docker logs -f $container; exec sh" &
                        ;;
                    "alacritty")
                        alacritty -t "$TITLE" -e sh -c "docker logs -f $container; exec sh" &
                        ;;
                    "wezterm")
                        wezterm start -- sh -c "docker logs -f $container; exec sh" &
                        ;;
                    "xterm")
                        xterm -T "$TITLE" -e "docker logs -f $container" &
                        ;;
                esac
            done
            LAUNCHED=true
            break
        fi
    done
fi

if [ "$LAUNCHED" = false ]; then
    echo "Error: Could not auto-detect a GUI terminal emulator or tmux."
    echo "You can stream logs manually in separate terminals using:"
    for container in "${CONTAINERS[@]}"; do
        echo "  docker logs -f $container"
    done
fi


