import argparse
import os
from glob import glob
from subprocess import run

import yaml

DEFAULTS = {
    "loop": True,
    "user": "pi",
    "gap": 0.0,
    "start_at": 0.0,
    "random": False,
}


def remote_run(player, command):
    """runs a remote command
    sets timeout to 5 seconds
    """

    user = player.get("user")
    host = player.get("host")
    command = f"""ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no {user}@{host} '{command}'"""
    run(command, shell=True)


def setup_system(player):
    '''
    Installs vlc if needed and creates the videos directory
    '''

    command = """if ! command -v vlc &> /dev/null
        then
            sudo apt-get update
            sudo apt-get -y install vlc
        fi
        mkdir -p ~/videos
        """
    remote_run(player, command)


def prepare_video_paths(player):
    videos = player.get("videos")

    if isinstance(videos, str):
        videos = [videos]

    videos = [glob(v) for v in videos]
    videos = [v for sublist in videos for v in sublist]
    return videos


def copy_videos(player):
    host = player.get("host")
    user = player.get("user")
    videos = player.get("videos")

    for v in videos:
        command = f"""rsync -avzP --ignore-existing {v} {user}@{host}:~/videos/"""
        run(command, shell=True)


def make_playlist(player):
    user = player.get("user")
    videos = player.get("videos")
    plist = [f"/home/{user}/videos/{os.path.basename(v)}" for v in videos]
    plist = "\n".join(plist)
    command = f"""echo "{plist}" > ~/playlist.m3u"""
    remote_run(player, command)


def create_service(player, service_type="bashrc"):
    user = player.get("user")
    vlc_args = ["cvlc", "--daemon", f"/home/{user}/playlist.m3u"]
    if player["loop"] is True:
        vlc_args += ["--loop"]

    if player["random"] is True:
        vlc_args += ["--random"]

    vlc_command = " ".join(vlc_args)

    if service_type=="bashrc":
        service = f"""
            if pgrep -x vlc >/dev/null
            then
                echo 'playing'
            else
                echo 'starting'
                {vlc_command}
            fi
        """

        command = f"""echo "{service}" > ~/start_player.sh; chmod u+x ~/start_player.sh"""
        remote_run(player, command)

        command = """grep -qxF '~/start_player.sh' ~/.bashrc || echo '~/start_player.sh' >> ~/.bashrc"""
        remote_run(player, command)

        remote_run(player, "killall -9 vlc")
        remote_run(player, "~/start_player.sh")
    else:
        service = f"""
            [Unit]
            Description=Video Player
            [Service]
            Type=simple
            TimeoutStartSec=0
            ExecStart={vlc_command}
            [Install]
            WantedBy=default.target
        """
        command = "mkdir -p ~/.local/share/systemd/user"
        remote_run(player, command)

        command = f"""echo "{service}" > ~/.local/share/systemd/user/player.service"""
        remote_run(player, command)


def restart_service(player):
    command = "systemctl --user enable player.service"
    remote_run(player, command)

    command = "systemctl --user restart player.service"
    remote_run(player, command)


def main(project_file=None, hosts=None, videos=None):
    settings = {}
    players = []

    if project_file:
        with open(project_file, "r") as infile:
            data = yaml.safe_load(infile)
            settings = data.get("settings", {})
            players = data.get("players", [])
    elif hosts is not None and videos is not None:
        for h in hosts:
            players.append({'host': h, 'videos': videos})

    # merge settings and defaults
    settings = {**DEFAULTS, **settings}

    # for each player, merge settings
    players = [{**settings, **p} for p in players]

    for p in players:
        p["videos"] = prepare_video_paths(p)
        setup_system(p)
        copy_videos(p)
        make_playlist(p)
        create_service(p)
        restart_service(p)


def extant_file(x):
    """
    'Type' for argparse - checks that file exists but does not open.
    From stackoverflow (todo: find original link)
    """
    if not os.path.exists(x):
        # Argparse uses the ArgumentTypeError to give a rejection message like:
        # error: argument input: x does not exist
        raise argparse.ArgumentTypeError("{0} does not exist".format(x))
    return x


def cli():
    parser = argparse.ArgumentParser(
        prog="PiPlayer",
        description="Easily setup and play videos on Raspberry Pi",
    )
    parser.add_argument("--project", help="Project file to load", type=extant_file)
    parser.add_argument(
        "--host", help="Hostname (leave blank if hostname is in the project file"
    )
    parser.add_argument("--video", help="Video file(s)", nargs="+")
    args = parser.parse_args()

    if not args.project or (not args.video and not args.host):
        parser.error("You must either specify a --project file or --video AND --host")

    main(project_file=args.project, hosts=args.host, videos=args.video)


if __name__ == "__main__":
    cli()
