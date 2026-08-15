/**
 * In-memory store for the MVP. Replaces a real database (PostgreSQL / sqlite)
 * so that the application has zero external infrastructure dependencies.
 *
 * Shape mirrors the `users` and `supplier_profiles` entities from TRD §6.
 */

export type Role = 'supplier' | 'buyer' | 'operator' | 'admin';
export type UserStatus = 'pending_verification' | 'active' | 'suspended';

export interface User {
  id: string;
  email: string;
  passwordHash: string;
  role: Role;
  status: UserStatus;
  emailVerificationToken: string | null;
  emailVerifiedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export type OwnershipStatus = 'owned' | 'leased' | 'cooperative';

export interface SupplierProfile {
  userId: string;
  /** Country / region where the farm is located */
  geography: string;
  /** Total farm area in hectares */
  landSizeHectares: number;
  /** Primary crop or livestock type */
  cropOrLivestockType: string;
  ownershipStatus: OwnershipStatus;
  /** Bank account / payment details (stored as opaque string for MVP) */
  payoutDetails: string;
  isComplete: boolean;
  createdAt: string;
  updatedAt: string;
}

// Singleton in-memory stores (reset per process – suitable for dev / tests)
export const usersStore = new Map<string, User>();
export const profilesStore = new Map<string, SupplierProfile>();
