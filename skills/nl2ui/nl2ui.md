---
name: generate_interactive_ui
description: "Natural Language to UI (NL2UI) generator. Use this when you need the user to confirm information, select options, or fill out a form with multiple parameters. DO NOT ask questions in plain text when these scenarios occur."
homepage: local
metadata:
  {
    "openclaw":
      {
        "emoji": "🎛️",
        "requires": {},
        "install": []
      }
  }
---

# Interactive UI Generation Skill

Transform natural language questions into structured UI components to improve user interaction efficiency.

## When to Use

✅ **USE this skill when:**
- You need the user to confirm an action (e.g., "Are you sure you want to deploy?")
- You need the user to choose from multiple options or strategies.
- You need to collect multiple parameters (e.g., server name, OS version, region).

## When NOT to Use

❌ **DON'T use this skill when:**
- The user is just asking for factual information.
- You only need a simple "yes" or "no" that doesn't affect a critical workflow.

## Output Rules (CRITICAL)

When you decide to use this skill, you must output a **pure JSON object** that conforms to the `Interactive Card Schema`. 
DO NOT wrap the JSON in markdown code blocks (like ```json). Just output the raw JSON starting with `{` and ending with `}`.
DO NOT output any other conversational text before or after the JSON.

## Interactive Card Schema Format

You must strictly follow this JSON structure:

{
  "ui_type": "interactive_card",
  "meta": {
    "task_id": "Generate a unique ID for this task to maintain context",
    "title": "Main title of the card",
    "description": "Short prompt or instruction for the user"
  },
  "elements": [
    // Use "input" for text fields
    {
      "type": "input",
      "id": "param_name",
      "label": "Display Label",
      "placeholder": "Example..."
    },
    // Use "select" for dropdowns/options
    {
      "type": "select",
      "id": "strategy",
      "label": "Choose Strategy",
      "options": [
        {"label": "Option A", "value": "opt_a"},
        {"label": "Option B", "value": "opt_b"}
      ],
      "default_value": "opt_a"
    }
  ],
  "actions": [
    {
      "action_type": "submit",
      "action_id": "confirm",
      "label": "Confirm & Submit",
      "theme": "primary"
    },
    {
      "action_type": "cancel",
      "action_id": "cancel",
      "label": "Cancel",
      "theme": "default"
    }
  ]
}