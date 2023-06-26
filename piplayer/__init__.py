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


class PiPlayer:
    def __init__(
        self,
        host,
        videos,
        user=DEFAULTS["user"],
        loop=DEFAULTS["loop"],
        random=DEFAULTS["random"],
        start_at=DEFAULTS["start_at"],
        gap=DEFAULTS["gap"],
    ):
        self.host = host
        self.videos = videos
        self.user = user
        self.loop = loop
        self.random = random
        self.start_at = start_at
        self.gap = gap

        self.command_queue = []

    def remote_run(self, command):
        self.command_queue.append(command)

    def send_commands(self):
        commands = "\n".join(self.command_queue)
        command = f"""ssh -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=no {self.user}@{self.host} '{commands}'"""
        self.command_queue = []
        run(command, shell=True)

    def create_folder(self):
        command = """mkdir -p ~/videos"""
        self.remote_run(command)

    def install_vlc(self):
        """
        Installs vlc if needed and creates the videos directory
        """

        command = """if ! command -v vlc &> /dev/null
            then
                sudo apt-get update
                sudo apt-get -y install vlc
            fi
            """
        self.remote_run(command)

    def prepare_video_paths(self):
        videos = self.videos

        if isinstance(videos, str):
            videos = [videos]

        videos = [glob(v) for v in videos]
        videos = [v for sublist in videos for v in sublist]

        self.videos = videos

    def copy_videos(self):
        self.create_folder()
        self.send_commands()

        for v in self.videos:
            command = f"""rsync -avzP --ignore-existing {v} {self.user}@{self.host}:~/videos/"""
            run(command, shell=True)

    def make_playlist(self):
        plist = [f"/home/{self.user}/videos/{os.path.basename(v)}" for v in self.videos]
        plist = "\n".join(plist)
        command = f"""echo "{plist}" > ~/playlist.m3u"""
        self.remote_run(command)

    def create_service(self, service_type="bashrc"):
        vlc_args = ["cvlc", "--daemon", "--no-osd", f"/home/{self.user}/playlist.m3u"]
        if self.loop is True:
            vlc_args += ["--loop"]

        if self.random is True:
            vlc_args += ["--random"]

        vlc_command = " ".join(vlc_args)

        if service_type == "bashrc":
            service = f"""
                if pgrep -x vlc >/dev/null
                then
                    echo 'playing'
                else
                    echo 'starting'
                    {vlc_command}
                fi
            """

            command = (
                f"""echo "{service}" > ~/start_player.sh; chmod u+x ~/start_player.sh"""
            )
            self.remote_run(command)

            command = """grep -qxF '~/start_player.sh' ~/.bashrc || echo '~/start_player.sh' >> ~/.bashrc"""
            self.remote_run(command)

            self.remote_run("killall -9 vlc")
            self.remote_run("~/start_player.sh")
        else:
            service = f"""
                [Unit]
                Description=Video Player
                [Service]
                Type=simple
                ExecStart={vlc_command}
                [Install]
                WantedBy=default.target
            """
            command = "mkdir -p ~/.local/share/systemd/user"
            self.remote_run(command)

            command = (
                f"""echo "{service}" > ~/.local/share/systemd/user/player.service"""
            )
            self.remote_run(command)

            self.remote_run("systemctl --user enable player.service")
            self.remote_run("systemctl --user daemon-reload")
            self.remote_run("systemctl --user restart player.service")

    def run(self):
        self.prepare_video_paths()
        self.copy_videos()
        self.install_vlc()
        self.make_playlist()
        self.create_service()
        self.send_commands()



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
            players.append({"host": h, "videos": videos})

    # merge settings and defaults
    settings = {**DEFAULTS, **settings}

    # for each player, merge settings
    players = [{**settings, **p} for p in players]

    for p in players:
        p = PiPlayer(**p)
        p.run()


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

    if args.project:
        main(project_file=args.project)
    elif args.video and args.host:
        main(hosts=args.host, videos=args.video)
    else:
        parser.error("You must either specify a --project file or --video AND --host")



if __name__ == "__main__":
    cli()
