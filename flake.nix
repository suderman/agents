{
  description = "Jon's agent packages and configuration";

  inputs.llm-agents.url = "github:numtide/llm-agents.nix";

  outputs = {llm-agents, ...}: {
    packages =
      builtins.mapAttrs (_: packages: {
        inherit (packages) opencode pi;
        default = packages.pi;
      })
      llm-agents.packages;
  };
}
