export type PropertyStatus = "free" | "listed_ykt" | "occupied";
export type PaymentStatus = "pending" | "paid" | "overdue";

export interface Property {
  id: string;
  name: string;
  address: string;
  status: PropertyStatus;
  owner_email: string;
  created_at: string;
  updated_at: string;
}

export interface Lease {
  id: string;
  property_id: string;
  tenant_name: string;
  tenant_email: string;
  rent_start: string;
  rent_end: string;
  payment_status: PaymentStatus;
  reminder_3d_sent_at: string | null;
  overdue_notice_sent_at: string | null;
  created_at: string;
}

export interface ConfirmInfo {
  lease_id: string;
  property_name: string;
  address: string;
  tenant_name: string;
  rent_end: string;
}
