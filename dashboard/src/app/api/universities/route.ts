import { NextResponse } from 'next/server'
import { UNIVERSITIES } from '@/lib/universities'

export async function GET() {
  return NextResponse.json({ universities: UNIVERSITIES, total: UNIVERSITIES.length })
}
