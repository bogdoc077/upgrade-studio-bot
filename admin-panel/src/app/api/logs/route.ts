import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET(request: Request) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('auth_token')?.value;
    
    if (!token) {
      return NextResponse.json({
        success: false,
        error: 'Unauthorized'
      }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const service = searchParams.get('service') || 'bot';
    const lines = searchParams.get('lines') || '100';

    const API_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001';
    
    const response = await fetch(`${API_URL}/api/logs/${service}?lines=${lines}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch logs');
    }
    
    const data = await response.json();
    
    return NextResponse.json(data);

  } catch (error) {
    console.error('Logs API error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch logs'
    }, { status: 500 });
  }
}
