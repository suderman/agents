{
  description = "Jon's agent packages and configuration";

  inputs.llm-agents.url = "github:numtide/llm-agents.nix";

  outputs = {llm-agents, ...}: {
    packages =
      builtins.mapAttrs (_: packages: let
        # Numtide's Bun binary omits codemode's worker; use its supported Node build.
        pi = (packages.pi.override {useBun = false;}).overrideAttrs (old: {
          postInstall =
            old.postInstall
            + ''
              wrapProgram "$out/bin/pi" \
                --set PI_PACKAGE_DIR "$out/lib/node_modules/@earendil-works/pi-coding-agent"
            '';
        });
      in {
        inherit (packages) hermes-agent opencode claude-code;
        inherit pi;
        default = pi;
      })
      llm-agents.packages;
  };
}
