/**
 * Authentication utilities – JWT signing/verification and password hashing.
 * TRD §4, §8.
 */

import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import type { Role } from '@/db/store';

const JWT_SECRET = process.env.JWT_SECRET ?? 'agro-future-dev-secret-change-in-prod';
const JWT_EXPIRES_IN = '7d';
const BCRYPT_ROUNDS = 10;

export interface TokenPayload {
  sub: string; // user id
  role: Role;
  email: string;
}

export function signToken(payload: TokenPayload): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
}

export function verifyToken(token: string): TokenPayload {
  return jwt.verify(token, JWT_SECRET) as TokenPayload;
}

export function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, BCRYPT_ROUNDS);
}

export function comparePassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}
