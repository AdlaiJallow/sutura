"use client";

import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/layout/empty-state";
import { ErrorState } from "@/components/layout/error-state";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { FinancialPeriod } from "@/lib/types";

/**
 * Shared plumbing for the three "period-scoped list of money-in records"
 * pages (Salary, Allowances, Income — CLAUDE.md explicitly warns against
 * duplicating this shape three times). One table + add/edit dialog + delete
 * confirmation + optimistic-lock retry, parameterized per module by its own
 * field set, table columns, and network calls — those stay in each page so
 * this file never has to know a Salary from an Allowance.
 *
 * Design note: Salary is "one per period" rather than a real list, but it's
 * rendered through the exact same table+dialog machinery with `maxRecords={1}`
 * (the Add action just disappears once a row exists) rather than a bespoke
 * "set your salary" form — one less pattern for the app to teach, and the
 * closed-period guard / optimistic-lock retry / validation UI all come for
 * free instead of being re-implemented a third time.
 */

export type MoneyInFieldValue = string | boolean;
export type MoneyInFormValues = Record<string, MoneyInFieldValue>;

export interface MoneyInFieldOption {
  value: string;
  label: string;
}

export interface MoneyInField {
  name: string;
  label: string;
  type: "text" | "textarea" | "amount" | "date" | "select" | "checkbox" | "currency";
  required?: boolean;
  placeholder?: string;
  helpText?: string;
  maxLength?: number;
  options?: MoneyInFieldOption[];
}

export interface MoneyInColumn<T> {
  header: string;
  className?: string;
  render: (record: T) => ReactNode;
}

export interface MoneyInRecordBase {
  id: string;
  updated_at: string;
}

export interface MoneyInManagerProps<T extends MoneyInRecordBase> {
  period: FinancialPeriod;
  fields: MoneyInField[];
  columns: MoneyInColumn<T>[];
  /** `null` while the initial list load is in flight. */
  records: T[] | null;
  error: string | null;
  addLabel: string;
  /** Lowercase noun for this record, e.g. "salary record", "allowance", "income entry". */
  singularLabel: string;
  emptyTitle: string;
  emptyMessage: string;
  /** Hides the Add action once this many records exist (1 for salary — D-008). */
  maxRecords?: number;
  /** Short line identifying a record for the delete-confirmation dialog, e.g. its name/description. */
  describeRecord: (record: T) => string;
  defaultValues: () => MoneyInFormValues;
  valuesFromRecord: (record: T) => MoneyInFormValues;
  onCreate: (values: MoneyInFormValues) => Promise<T>;
  onUpdate: (id: string, values: MoneyInFormValues, expectedUpdatedAt: string) => Promise<T>;
  onDelete: (id: string) => Promise<void>;
  onReload: () => void;
}

function todayISODate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function defaultDateReceived(): string {
  return todayISODate();
}

function validateValues(fields: MoneyInField[], values: MoneyInFormValues): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fields) {
    if (field.type === "checkbox") continue;
    const raw = values[field.name];
    const str = typeof raw === "string" ? raw.trim() : "";

    if (field.required && !str) {
      errors[field.name] = `${field.label} is required.`;
      continue;
    }
    if (!str) continue;

    if (field.type === "amount" && !/^\d+(\.\d{1,4})?$/.test(str)) {
      errors[field.name] = "Enter an amount of 0 or more, e.g. 1500 or 1500.50.";
    }
    if (field.type === "currency" && !/^[A-Za-z]{3}$/.test(str)) {
      errors[field.name] = "Currency must be a 3-letter code, e.g. GMD.";
    }
  }
  return errors;
}

/** Normalizes form state into a plain JSON-ready payload: trims text, uppercases
 * currency codes, and turns blank optional fields into `null` so clearing a
 * field on edit actually clears it server-side rather than being silently
 * dropped. Amounts are passed through as the exact string the user typed —
 * never `Number(...)`-parsed — so Decimal precision is never touched here. */
function normalizeValues(fields: MoneyInField[], values: MoneyInFormValues): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const field of fields) {
    const raw = values[field.name];
    if (field.type === "checkbox") {
      out[field.name] = Boolean(raw);
      continue;
    }
    const str = typeof raw === "string" ? raw.trim() : "";
    if (field.type === "currency") {
      out[field.name] = str.toUpperCase();
    } else if (!str) {
      out[field.name] = field.required ? str : null;
    } else {
      out[field.name] = str;
    }
  }
  return out;
}

export function MoneyInManager<T extends MoneyInRecordBase>({
  period,
  fields,
  columns,
  records,
  error,
  addLabel,
  singularLabel,
  emptyTitle,
  emptyMessage,
  maxRecords,
  describeRecord,
  defaultValues,
  valuesFromRecord,
  onCreate,
  onUpdate,
  onDelete,
  onReload,
}: MoneyInManagerProps<T>) {
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<T | null>(null);
  const [deleting, setDeleting] = useState<T | null>(null);

  const isClosed = period.status === "CLOSED";
  const atLimit = typeof maxRecords === "number" && (records?.length ?? 0) >= maxRecords;

  async function handleCreate(values: MoneyInFormValues) {
    const created = await onCreate(normalizeValues(fields, values) as MoneyInFormValues);
    setAddOpen(false);
    onReload();
    return created;
  }

  async function handleUpdate(id: string, values: MoneyInFormValues, expectedUpdatedAt: string) {
    const updated = await onUpdate(id, normalizeValues(fields, values) as MoneyInFormValues, expectedUpdatedAt);
    setEditing(null);
    onReload();
    return updated;
  }

  async function handleConfirmDelete() {
    if (!deleting) return;
    await onDelete(deleting.id);
    setDeleting(null);
    onReload();
  }

  return (
    <div className="space-y-4">
      {isClosed && (
        <div className="rounded-md border border-line bg-secondary px-4 py-3 text-sm text-ink-soft">
          This period is closed, so it can&apos;t be edited here.{" "}
          <Link href={`/financial-periods/${period.id}`} className="font-medium text-rust-500 hover:text-rust-700">
            Reopen it
          </Link>{" "}
          first if you need to add or change a record.
        </div>
      )}

      <div className="flex justify-end">
        {!isClosed && !atLimit && (
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button>{addLabel}</Button>
            </DialogTrigger>
            <DialogContent>
              <RecordForm
                title={addLabel}
                fields={fields}
                initialValues={defaultValues()}
                submitLabel="Save"
                onSubmit={handleCreate}
              />
            </DialogContent>
          </Dialog>
        )}
      </div>

      {error && <ErrorState message={error} onRetry={onReload} />}

      {!error && records === null && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-md bg-secondary" />
          ))}
        </div>
      )}

      {!error && records !== null && records.length === 0 && (
        <EmptyState
          title={emptyTitle}
          message={emptyMessage}
          action={
            !isClosed && (
              <Button onClick={() => setAddOpen(true)}>{addLabel}</Button>
            )
          }
        />
      )}

      {!error && records !== null && records.length > 0 && (
        <div className="overflow-hidden rounded-md border border-line">
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((col) => (
                  <TableHead key={col.header} className={col.className}>
                    {col.header}
                  </TableHead>
                ))}
                <TableHead className="text-right">&nbsp;</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.map((record) => (
                <TableRow key={record.id}>
                  {columns.map((col) => (
                    <TableCell key={col.header} className={col.className}>
                      {col.render(record)}
                    </TableCell>
                  ))}
                  <TableCell className="text-right whitespace-nowrap">
                    {!isClosed && (
                      <>
                        <button
                          type="button"
                          onClick={() => setEditing(record)}
                          className="text-sm font-medium text-rust-500 hover:text-rust-700"
                        >
                          Edit
                        </button>
                        <span className="mx-2 text-line">|</span>
                        <button
                          type="button"
                          onClick={() => setDeleting(record)}
                          className="text-sm font-medium text-overspent hover:text-overspent/80"
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          {editing && (
            <RecordForm
              title={`Edit this ${singularLabel}`}
              fields={fields}
              initialValues={valuesFromRecord(editing)}
              submitLabel="Save changes"
              onSubmit={(values) => handleUpdate(editing.id, values, editing.updated_at)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <DialogContent>
          {deleting && (
            <DeleteConfirm
              description={describeRecord(deleting)}
              singularLabel={singularLabel}
              onConfirm={handleConfirmDelete}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function DeleteConfirm({
  description,
  singularLabel,
  onConfirm,
}: {
  description: string;
  singularLabel: string;
  onConfirm: () => Promise<void>;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleClick() {
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await onConfirm();
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : `Couldn't delete this ${singularLabel}.`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <DialogHeader>
        <DialogTitle>Delete this {singularLabel}?</DialogTitle>
        <DialogDescription>
          &quot;{description}&quot; will be permanently removed from this period. This can&apos;t be undone.
        </DialogDescription>
      </DialogHeader>
      {errorMessage && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {errorMessage}
        </p>
      )}
      <DialogFooter>
        <Button variant="destructive" onClick={handleClick} disabled={submitting}>
          {submitting ? "Deleting…" : "Delete"}
        </Button>
      </DialogFooter>
    </div>
  );
}

function RecordForm({
  title,
  fields,
  initialValues,
  submitLabel,
  onSubmit,
}: {
  title: string;
  fields: MoneyInField[];
  initialValues: MoneyInFormValues;
  submitLabel: string;
  onSubmit: (values: MoneyInFormValues) => Promise<unknown>;
}) {
  const [values, setValues] = useState<MoneyInFormValues>(initialValues);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function setField(name: string, value: MoneyInFieldValue) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errors = validateValues(fields, values);
    setFieldErrors(errors);
    setBanner(null);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await onSubmit(values);
    } catch (err) {
      if (err instanceof ApiError) {
        const mapped: Record<string, string> = {};
        for (const fe of err.fieldErrors ?? []) {
          mapped[fe.field] = fe.message;
        }
        setFieldErrors(mapped);
        // A closed-period or stale-update conflict has no field to attach to —
        // it always gets the plain-language banner so it never looks like a
        // silent failure (spec: surface 409s clearly, not as a generic error).
        if (Object.keys(mapped).length === 0 || err.status === 409) {
          setBanner(err.message);
        }
      } else {
        setBanner("Something went wrong saving this. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>

      {banner && (
        <p role="alert" className="rounded-md bg-overspent-bg px-3 py-2 text-sm text-overspent">
          {banner}
        </p>
      )}

      <div className="space-y-3">
        {fields.map((field) => (
          <FieldControl
            key={field.name}
            field={field}
            value={values[field.name]}
            error={fieldErrors[field.name]}
            onChange={(v) => setField(field.name, v)}
          />
        ))}
      </div>

      <DialogFooter>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : submitLabel}
        </Button>
      </DialogFooter>
    </form>
  );
}

function FieldControl({
  field,
  value,
  error,
  onChange,
}: {
  field: MoneyInField;
  value: MoneyInFieldValue | undefined;
  error?: string;
  onChange: (value: MoneyInFieldValue) => void;
}) {
  const id = `field-${field.name}`;

  if (field.type === "checkbox") {
    return (
      <label htmlFor={id} className="flex items-center gap-2 text-sm text-ink">
        <input
          id={id}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          className="size-4 rounded border-line accent-rust-500"
        />
        {field.label}
      </label>
    );
  }

  const stringValue = typeof value === "string" ? value : "";

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{field.label}</Label>
      {field.type === "textarea" && (
        <textarea
          id={id}
          value={stringValue}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          placeholder={field.placeholder}
          className="w-full rounded-md border border-line bg-card px-3 py-2 text-sm text-ink outline-none focus-visible:border-rust-500"
        />
      )}
      {field.type === "select" && (
        <Select value={stringValue} onValueChange={onChange}>
          <SelectTrigger id={id} className="w-full">
            <SelectValue placeholder={field.placeholder ?? "Choose one"} />
          </SelectTrigger>
          <SelectContent>
            {(field.options ?? []).map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      {field.type === "date" && (
        <Input id={id} type="date" value={stringValue} onChange={(e) => onChange(e.target.value)} />
      )}
      {field.type === "amount" && (
        <Input
          id={id}
          inputMode="decimal"
          value={stringValue}
          placeholder={field.placeholder ?? "0.00"}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {field.type === "currency" && (
        <Input
          id={id}
          value={stringValue}
          maxLength={field.maxLength ?? 3}
          onChange={(e) => onChange(e.target.value.toUpperCase())}
          className={cn("w-24 uppercase")}
        />
      )}
      {field.type === "text" && (
        <Input
          id={id}
          value={stringValue}
          placeholder={field.placeholder}
          maxLength={field.maxLength}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {field.helpText && !error && <p className="text-xs text-ink-faint">{field.helpText}</p>}
      {error && <p className="text-xs text-overspent">{error}</p>}
    </div>
  );
}
