# Claude and Codex

The same SKILL.md uses portable `name/description` frontmatter. Paths below are for local agents, not an assumption that a chat session can access your Blender machine.

- Claude Code personal: `~/.claude/skills/r6-animator/`; project: `.claude/skills/r6-animator/`.
- Codex local skills: `~/.agents/skills/r6-animator/`; project: `.agents/skills/r6-animator/`. Managed ChatGPT skill installation follows its Skills UI.
- Claude web/API/Cowork: use the platform's supported skill-upload flow if available. Skill availability does not itself connect a remote Blender instance. Inspect the actual runtime capabilities.

`scripts/install.py --client claude|codex --scope user|project --project PATH` copies this portable skill to the corresponding local folder. `--dest PATH` selects an explicit skill parent. Existing destinations are preserved unless `--replace` is explicit; replacement creates a backup first. Run only when the user asks to install. `--check` performs offline diagnostics; `--boot` prints a Blender import line. `--mcp-config` prints a companion configuration; it does not edit client settings.

The stdio companion `scripts/mcp_server.py` provides reference summaries, authored-table lint/QA/offline previews, video-media preparation and R6 export. It does not control Blender and it does not perform visual reasoning. Configure its Python command and absolute script path through the client's supported MCP interface. Blender's separate MCP extension is required for interactive Blender execution, or use the local Blender executable with Python.

Discover real tool names each session. Common official Blender Lab capabilities include executing Blender Python and capturing rendered/UI images; do not require one vendor's exact names. Check source/API docs for the installed Blender version when code fails. Use local Blender background execution when it is available and appropriate.

Optional dependencies: Pillow for timestamped video sheets; FFmpeg/ffprobe for media preparation; yt-dlp for supported public URLs; matplotlib/numpy for offline R6 box previews. Missing network/auth/media access must be reported. Never claim a tool inspected a video when it only downloaded media.

Documentation verified 2026-10-01:
- Claude skills: https://code.claude.com/docs/en/skills
- OpenAI skills: https://learn.chatgpt.com/docs/build-skills
- Official Blender MCP (5.1+): https://www.blender.org/lab/mcp-server/
- Blender action slots: https://developer.blender.org/docs/release_notes/4.4/upgrading/slotted_actions/
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- FFmpeg: https://ffmpeg.org/ffmpeg.html

Installation and network features depend on the user's environment. The common authoring workflow is shared; tool execution must be tested in each client rather than inferred from valid Markdown.
