export interface PatrolWorkflowRules {
  status_order: string[]
  initial_status: string
  actions: string[]
  negative_actions: string[]
  transitions: Record<string, Record<string, string>>
  status_flags: Record<string, { pending: boolean; abnormal: boolean }>
}

export function patrolStatus(row: Record<string, unknown>): string {
  return String(row.status ?? '')
}

export function allowedPatrolActions(
  row: Record<string, unknown>,
  rules: PatrolWorkflowRules | null,
): string[] {
  if (rules === null) {
    return []
  }
  const transitions = rules.transitions[patrolStatus(row)] ?? {}
  return rules.actions.filter((action) =>
    Object.prototype.hasOwnProperty.call(transitions, action),
  )
}
