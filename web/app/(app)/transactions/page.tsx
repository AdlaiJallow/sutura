"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { BankTransactionsList } from "@/components/finance/bank-transactions-list";
import { TransactionForm } from "@/components/finance/transaction-form";
import { TransferForm } from "@/components/finance/transfer-form";
import { EmptyState } from "@/components/layout/empty-state";
import { usePeriod } from "@/components/layout/period-context";
import { api, ApiError } from "@/lib/api";
import { monthLabel } from "@/lib/text";
import { useMoneyInList } from "@/lib/use-money-in-list";
import type { BankAccountSummary } from "@/lib/types";

/**
 * A period-scoped, append-only ledger view (spec/task brief: no PATCH/DELETE
 * exists on `/bank-transactions`, so only create + list are built here — see
 * `BankTransactionsList`). Bank accounts themselves are fetched here (not
 * period-scoped, but needed to resolve names/masked ids and to populate the
 * "which account" pickers) rather than duplicated per dialog.
 */
export default function TransactionsPage() {
  const { period } = usePeriod();
  const isClosed = period.status === "CLOSED";

  const [accounts, setAccounts] = useState<BankAccountSummary[] | null>(null);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [filterAccountId, setFilterAccountId] = useState<string>("all");
  const [addOpen, setAddOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);

  const loadAccounts = useCallback(async () => {
    setAccountsError(null);
    try {
      const res = await api.bankAccounts.list({ page_size: 100 });
      setAccounts(res.data);
    } catch (err) {
      setAccountsError(err instanceof ApiError ? err.message : "Couldn't load your bank accounts.");
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await loadAccounts();
    })();
  }, [loadAccounts]);

  const fetchTransactions = useCallback(
    () =>
      api.bankTransactions.list({
        financial_period_id: period.id,
        bank_account_id: filterAccountId === "all" ? undefined : filterAccountId,
        page_size: 100,
      }),
    [period.id, filterAccountId],
  );
  const { records: transactions, error: transactionsError, reload: reloadTransactions } = useMoneyInList(fetchTransactions);

  async function reloadAll() {
    await Promise.all([loadAccounts(), reloadTransactions()]);
  }

  const activeAccounts = (accounts ?? []).filter((a) => a.is_active);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-ink">Transactions</h1>
          <p className="mt-1 max-w-lg text-sm text-ink-soft">
            A running record of deposits, withdrawals, and transfers in {monthLabel(period.year, period.month)} —
            every row here is permanent once it&apos;s posted.
          </p>
        </div>
        {!isClosed && activeAccounts.length > 0 && (
          <div className="flex gap-2">
            <Dialog open={transferOpen} onOpenChange={setTransferOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">Transfer money</Button>
              </DialogTrigger>
              <DialogContent>
                {transferOpen && (
                  <TransferForm
                    accounts={activeAccounts}
                    onSubmit={async (payload) => {
                      await api.bankTransactions.transfer({ ...payload, financial_period_id: period.id });
                      setTransferOpen(false);
                      await reloadAll();
                    }}
                  />
                )}
              </DialogContent>
            </Dialog>
            <Dialog open={addOpen} onOpenChange={setAddOpen}>
              <DialogTrigger asChild>
                <Button>Add transaction</Button>
              </DialogTrigger>
              <DialogContent>
                {addOpen && (
                  <TransactionForm
                    accounts={activeAccounts}
                    onSubmit={async (payload) => {
                      await api.bankTransactions.create({ ...payload, financial_period_id: period.id });
                      setAddOpen(false);
                      await reloadAll();
                    }}
                  />
                )}
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {isClosed && (
        <div className="rounded-md border border-line bg-secondary px-4 py-3 text-sm text-ink-soft">
          This period is closed, so new transactions can&apos;t be posted to it here.
        </div>
      )}
      {!isClosed && (accounts !== null && activeAccounts.length === 0) && (
        <div className="rounded-md border border-line bg-secondary px-4 py-3 text-sm text-ink-soft">
          Add an active bank account first to record deposits, withdrawals, or transfers.
        </div>
      )}

      {accounts !== null && accounts.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium tracking-wideish text-ink-faint uppercase">Account</span>
          <Select value={filterAccountId} onValueChange={setFilterAccountId}>
            <SelectTrigger className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All accounts</SelectItem>
              {accounts.map((a) => (
                <SelectItem key={a.id} value={a.id}>
                  {a.account_identifier_last4 ? `${a.account_name} ••${a.account_identifier_last4}` : a.account_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {(accountsError || transactionsError) && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {accountsError ?? transactionsError}
        </p>
      )}

      {transactions === null && !transactionsError && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-md bg-secondary" />
          ))}
        </div>
      )}

      {transactions !== null && transactions.length === 0 && (
        <EmptyState
          title="No transactions yet"
          message={`Nothing has been posted to your accounts for ${monthLabel(period.year, period.month)} yet.`}
        />
      )}

      {transactions !== null && transactions.length > 0 && (
        <BankTransactionsList transactions={transactions} accounts={accounts ?? []} />
      )}
    </div>
  );
}
