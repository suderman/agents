{
  description = "Jon's agent packages and configuration";

  inputs.llm-agents.url = "github:numtide/llm-agents.nix";

  outputs = {llm-agents, ...}: {
    packages =
      builtins.mapAttrs (_: packages: let
        # Numtide's Bun binary omits codemode's worker; use its supported Node build.
        pi = (packages.pi.override {useBun = false;}).overrideAttrs (old: {
          postPatch =
            (old.postPatch or "")
            + ''
              substituteInPlace dist/utils/clipboard.js --replace-fail \
                '    const env = process.env;' \
                '    const env = process.env;
                  // Herdr owns the client clipboard; this display may belong to another host.
                  if (env.HERDR_ENV === "1") {
                      if (emitOsc52(text))
                          return;
                      throw new Error("Clipboard unavailable: text exceeds the OSC 52 size limit");
                  }'
              # The Node CLI runs the bundle; SDK callers use the module above.
              clipboard_bundle="$(grep -lF 'async function copyToClipboard(text){' dist/bundle/chunks/*.js)"
              substituteInPlace "$clipboard_bundle" --replace-fail \
                'async function copyToClipboard(text){' \
                'async function copyToClipboard(text){if(process.env.HERDR_ENV==="1"){if(emitOsc52(text))return;throw new Error("Clipboard unavailable: text exceeds the OSC 52 size limit");}'
            '';
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
