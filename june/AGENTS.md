# June's operating conventions

- Org files under `~/org` are the authority for tasks, projects, notes, and long-term facts. Herdr is the authority for live agent sessions. The conversation transcript is short-term continuity only, so look facts up with your tools instead of trusting memory, and verify anything with a date against Org.
- Projects live at `~/org/work/<domain>/<project>/<project>.org`. Each first-level heading is one task or thread, and its `Sessions` section links the Herdr sessions that worked on it.
- Task states are TODO (not started), PROG (in progress), EVAL (waiting for Jon's review), HOLD (blocked or waiting), and DONE. Do not invent other states.
- AUTO marks a task for the org-dispatch dispatcher, which starts a Pi agent in Herdr on the host named by the task's tag: kit, cog, or lux. Only Jon sets AUTO.
- To answer what an agent is doing, inspect Herdr directly. To start new work, find or describe the Org task and ask Jon to queue it. Do not act as a second dispatcher.
- A Herdr status of idle or done means the terminal settled, not that the task succeeded. Read the output and the task's Org state before reporting success. blocked means the agent waits for a person.
- kit is the always-on desktop and runs June. cog is the laptop and is often asleep. lux is the headless media server.
