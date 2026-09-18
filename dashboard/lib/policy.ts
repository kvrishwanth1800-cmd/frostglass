// Entity-type taxonomy for the policy matrix (H.6.2 page 4). Grouping is a
// presentation concern; the entity-type strings match what the detection
// engine emits (see tests/unit/test_detection_*). Company terms come from
// dictionaries and custom recognizers.
export const ENTITY_GROUPS: { group: string; entity_types: string[] }[] = [
  { group: "Identity", entity_types: ["PERSON", "EMAIL", "PHONE", "LOCATION", "ORGANIZATION"] },
  { group: "Financial", entity_types: ["CREDIT_CARD", "IBAN", "US_SSN"] },
  { group: "Health", entity_types: ["MEDICAL_RECORD", "HEALTH_CONDITION"] },
  {
    group: "Credentials",
    entity_types: [
      "AWS_ACCESS_KEY",
      "GITHUB_TOKEN",
      "SLACK_TOKEN",
      "STRIPE_KEY",
      "OPENAI_KEY",
      "ANTHROPIC_KEY",
      "JWT",
      "PRIVATE_KEY",
      "HIGH_ENTROPY_TOKEN",
      "PASSWORD",
    ],
  },
  { group: "Company terms", entity_types: ["PROJECT_CODENAME"] },
];

export const ACTIONS = ["allow", "pseudonymize", "tag", "hash", "block"] as const;
export type PolicyAction = (typeof ACTIONS)[number];

export interface MatrixRow {
  entity_type: string;
  action: PolicyAction;
  min_confidence: number;
}

import type { RuleSetView } from "@/lib/types";

// Flatten the active ruleset into one action + confidence per entity type. A
// rule may cover several entity types; the first rule that names a type wins,
// otherwise the default action applies. This is the inverse of buildPolicyYaml.
export function matrixFromRuleset(ruleset: RuleSetView): MatrixRow[] {
  const rows: MatrixRow[] = [];
  const seen = new Set<string>();
  for (const { entity_types } of ENTITY_GROUPS) {
    for (const entity_type of entity_types) {
      if (seen.has(entity_type)) continue;
      seen.add(entity_type);
      const rule = ruleset.rules.find((candidate) => candidate.entity_types.includes(entity_type));
      rows.push({
        entity_type,
        action: (rule?.action as PolicyAction) ?? (ruleset.default_action as PolicyAction),
        min_confidence: rule?.min_confidence ?? 0.5,
      });
    }
  }
  return rows;
}

// Generate a valid policy YAML document (loader.load_yaml contract): a
// positive integer version, a default_action, and one rule per entity type
// whose action differs from the default. Scope teams, when given, restrict the
// rule to those teams.
export function buildPolicyYaml(
  rows: MatrixRow[],
  version: number,
  defaultAction: PolicyAction,
  scopeTeams: string[],
): string {
  const lines: string[] = [`version: ${version}`, `default_action: ${defaultAction}`, "rules:"];
  const changed = rows.filter((row) => row.action !== defaultAction);
  if (changed.length === 0) {
    lines.push(" []");
    return lines.join("\n").replace("rules:\n []", "rules: []");
  }
  for (const row of changed) {
    lines.push(`  - id: ${row.entity_type.toLowerCase()}-rule`);
    lines.push(`    entity_types: [${row.entity_type}]`);
    lines.push(`    action: ${row.action}`);
    lines.push(`    min_confidence: ${row.min_confidence.toFixed(2)}`);
    lines.push(`    reason: Set via policy editor.`);
    if (scopeTeams.length > 0) {
      lines.push(`    scope:`);
      lines.push(`      teams: [${scopeTeams.join(", ")}]`);
    }
  }
  return lines.join("\n");
}
