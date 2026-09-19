import { cn } from "@/lib/utils";
import { AmountDisplay } from "./amount-display";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatLedgerDate } from "@/lib/money";
import { humanizeEnum } from "@/lib/text";
import type { BankAccountSummary, BankTransaction } from "@/lib/types";

export interface BankTransactionsListProps {
  transactions: BankTransaction[];
  accounts: BankAccountSummary[];
}

const INFLOW_TYPES = new Set(["DEPOSIT", "TRANSFER_IN"]);
const OUTFLOW_TYPES = new Set(["WITHDRAWAL", "TRANSFER_OUT"]);

function directionTone(type: string): "positive" | "negative" | "neutral" {
  if (INFLOW_TYPES.has(type)) return "positive";
  if (OUTFLOW_TYPES.has(type)) return "negative";
  return "neutral";
}

const TYPE_BADGE_CLASSES: Record<"positive" | "negative" | "neutral", string> = {
  positive: "bg-ontrack-bg text-ontrack",
  negative: "bg-overspent-bg text-overspent",
  neutral: "bg-secondary text-ink-soft",
};

function TransactionTypeBadge({ type }: { type: string }) {
  const tone = directionTone(type);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold tracking-wideish uppercase",
        TYPE_BADGE_CLASSES[tone],
      )}
    >
      <span className="size-1.5 shrink-0 rounded-full bg-current" aria-hidden />
      {humanizeEnum(type)}
    </span>
  );
}

function accountLabel(account: BankAccountSummary | undefined): string {
  if (!account) return "Unknown account";
  return account.account_identifier_last4
    ? `${account.account_name} ••${account.account_identifier_last4}`
    : account.account_name;
}

/**
 * Pure presentational ledger table — an append-only view (spec/task brief:
 * no PATCH/DELETE exists on the backend, so no row here is ever editable).
 * Direction (money in vs out) is shown with color and the transaction type's
 * own label, never by prefixing a computed sign onto the amount — the amount
 * itself is exactly what `GET /bank-transactions` returned (CLAUDE.md: never
 * re-derive a financial figure client-side, not even a display sign).
 */
export function BankTransactionsList({ transactions, accounts }: BankTransactionsListProps) {
  const accountsById = new Map(accounts.map((a) => [a.id, a]));

  return (
    <div className="overflow-hidden rounded-md border border-line">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Account</TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            <TableHead>Description</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {transactions.map((txn) => (
            <TableRow key={txn.id}>
              <TableCell className="figure text-xs text-ink-faint">{formatLedgerDate(txn.transaction_date)}</TableCell>
              <TableCell className="text-ink">{accountLabel(accountsById.get(txn.bank_account_id))}</TableCell>
              <TableCell>
                <TransactionTypeBadge type={txn.transaction_type} />
              </TableCell>
              <TableCell className="text-right">
                <AmountDisplay value={txn.amount} currency={txn.currency} tone={directionTone(txn.transaction_type)} />
              </TableCell>
              <TableCell className="max-w-xs truncate text-xs text-ink-faint">{txn.description ?? "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
