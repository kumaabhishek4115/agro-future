/**
 * Shared API helpers – response builders and request authentication guard.
 * TRD §4, §7, §8.
 */

import { NextRequest, NextResponse } from 'next/server';
import { verifyToken, type TokenPayload } from '@/lib/auth';
import type { Role } from '@/db/store';

export function ok<T>(data: T, status = 200): NextResponse {
  return NextResponse.json({ success: true, data }, { status });
}

export function err(message: string, status: number): NextResponse {
  return NextResponse.json({ success: false, error: message }, { status });
}

/**
 * Extract and verify the ****** from the Authorization header.
 * Returns the decoded payload or throws a 401 response.
 */
export function requireAuth(req: NextRequest): TokenPayload {
  const authHeader = req.headers.get('authorization') ?? '';
  const [scheme, token] = authHeader.split(' ');
  if (scheme !== 'Bearer' || !token) {
    throw NextResponse.json(
      { success: false, error: 'Authentication required' },
      { status: 401 },
    );
  }
  try {
    return verifyToken(token);
  } catch {
    throw NextResponse.json(
      { success: false, error: 'Invalid or expired token' },
      { status: 401 },
    );
  }
}

/**
 * Require the caller to have one of the listed roles.
 */
export function requireRole(payload: TokenPayload, ...roles: Role[]): void {
  if (!roles.includes(payload.role)) {
    throw NextResponse.json(
      { success: false, error: 'Forbidden' },
      { status: 403 },
    );
  }
}
