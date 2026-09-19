import { cn } from "@/lib/utils";
import { humanizeEnum } from "@/lib/text";
import { AmountDisplay } from "./amount-display";
import { StatusBadge } from "./status-badge";
import type { BankAccountSummary } from "@/lib/types";

export interface BankAccountListProps {
  accounts: BankAccountSummary[];
  onEdit: (account: BankAccountSummary) => void;
  onToggleActive: (account: BankAccountSummary) => void;
}

/**
 * Pure presentational grid of account cards — split out of
 * `bank-account-manager.tsx` (which owns the fetch + dialogs, same split as
 * `distribution-rule-manager.tsx`'s `RuleCard`) so the two things this page
 * must never get wrong — masking the account identifier (spec §35/D-034/D-015:
 * `account_identifier_last4` only, never a full number) and showing an
 * inactive account as visually distinct rather than silently the same as an
 * active one — are directly testable with plain fixture props.
 */
export function BankAccountList({ accounts, onEdit, onToggleActive }: BankAccountListProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {accounts.map((account) => (
        <div
          key={account.id}
          className={cn(
            "rounded-md border border-line bg-card p-4 transition-colors duration-250 ease-ledger",
            !account.is_active && "bg-secondary/40 opacity-75",
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-display text-lg text-ink">{account.account_name}</p>
              <p className="text-xs text-ink-faint">{account.institution_name ?? "No institution on file"}</p>
            </div>
            <StatusBadge status={account.is_active ? "ACTIVE" : "INACTIVE"} />
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-ink-soft">
            {account.account_type && (
              <span className="rounded-full bg-secondary px-2 py-0.5 font-medium tracking-wideish text-ink-soft uppercase">
                {humanizeEnum(account.account_type)}
              </span>
            )}
            <span className="figure">
              {account.account_identifier_last4 ? `•••• ${account.account_identifier_last4}` : "No identifier on file"}
            </span>
          </div>

          <AmountDisplay value={account.current_balance} currency={account.currency} size="lg" className="mt-3" />
          <p className="mt-0.5 text-xs text-ink-faint">Current balance</p>

          <div className="mt-4 flex gap-3 text-sm font-medium">
            <button type="button" onClick={() => onEdit(account)} className="text-rust-500 hover:text-rust-700">
              Edit
            </button>
            <button
              type="button"
              onClick={() => onToggleActive(account)}
              className={account.is_active ? "text-overspent hover:text-overspent/80" : "text-ontrack hover:text-ontrack/80"}
            >
              {account.is_active ? "Deactivate" : "Reactivate"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
