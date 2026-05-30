export type PropertyStatus = "free" | "listed_ykt" | "occupied";
export type PeriodStatus = "pending" | "paid" | "overdue";

export interface Property {
  id: string;
  name: string;
  address: string;
  status: PropertyStatus;
  owner_email: string;
  created_at: string;
  updated_at: string;
}

export interface RentPeriod {
  id: string;
  lease_id: string;
  year: number;
  month: number;
  due_date: string;
  amount_due: number;
  amount_paid: number;
  status: PeriodStatus;
  reminder_3d_sent_at: string | null;
  overdue_notice_sent_at: string | null;
  paid_at: string | null;
}

export interface Lease {
  id: string;
  property_id: string;
  tenant_name: string;
  tenant_email: string;
  rent_start: string;
  rent_end: string;
  rent_amount: number;
  payment_day: number;
  contract_number: string | null;
  contract_date: string | null;
  terminated_at: string | null;
  created_at: string;
  periods: RentPeriod[];
}

export interface ConfirmInfo {
  period_id: string;
  property_name: string;
  address: string;
  tenant_name: string;
  year: number;
  month: number;
  due_date: string;
  amount_due: number;
  amount_paid: number;
  status: PeriodStatus;
}
