{
  config,
  lib,
  pkgs,
  ...
}: {
  options.programs.agents.enable = lib.mkEnableOption "the agents launcher for a writable ~/.agents checkout";

  config = lib.mkIf config.programs.agents.enable {
    home.packages = [
      (pkgs.writeShellApplication {
        name = "agents";
        runtimeInputs = with pkgs; [bash coreutils diffutils git jq python3 yq-go];
        text = ''
          if [[ ! -f "$HOME/.agents/agents" ]]; then
            echo "Missing agents checkout at $HOME/.agents; clone https://github.com/suderman/agents.git there." >&2
            exit 1
          fi
          exec python3 "$HOME/.agents/agents" "$@"
        '';
      })
    ];
  };
}
