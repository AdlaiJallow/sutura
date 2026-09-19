"use client";

import { BankAccountsManager } from "@/components/finance/bank-account-manager";

/**
 * Not period-scoped (accounts persist across periods, spec §32/task brief) —
 * deliberately does not read `usePeriod()`. All the fetching/CRUD logic lives
 * in `BankAccountsManager` itself, the same self-contained-manager shape as
 * `DistributionRulesManager`.
 */
export default function BankAccountsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">Bank Accounts</h1>
        <p className="mt-1 max-w-lg text-sm text-ink-soft">
          Your accounts and mobile wallets, with masked account numbers and running balances that
          update as you deposit, withdraw, and transfer.
        </p>
      </div>

      <BankAccountsManager />
    </div>
  );
}
