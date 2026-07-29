// Shared client-side retirement math — mirrors the server's deterministic
// projection so any page can compute what-ifs instantly.

export const INFLATION = 2.5

export interface RetireInputs {
  current_age: number
  retire_age: number
  current_assets: number
  monthly_contribution: number
  monthly_spending: number
  expected_return_pct: number
}

export function projectLocal(inp: RetireInputs) {
  const years = Math.max(0, inp.retire_age - inp.current_age)
  const realReturn = (1 + inp.expected_return_pct / 100) / (1 + INFLATION / 100) - 1
  const path: { age: number; balance: number }[] = []
  let balance = inp.current_assets
  let millionAge: number | null = null
  for (let y = 0; y <= years; y++) {
    path.push({ age: inp.current_age + y, balance: Math.round(balance) })
    if (millionAge === null && balance >= 1_000_000) millionAge = inp.current_age + y
    balance = balance * (1 + realReturn) + inp.monthly_contribution * 12
  }
  const projected = path[path.length - 1]?.balance ?? inp.current_assets
  return { path, projected, safeMonthly: Math.round(projected * 0.04 / 12), millionAge }
}
