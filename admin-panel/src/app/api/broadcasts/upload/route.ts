import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    
    // Отримуємо токен авторизації
    const authHeader = request.headers.get('authorization');
    if (!authHeader) {
      return NextResponse.json(
        { success: false, error: 'Authorization required' },
        { status: 401 }
      );
    }

    // Пересилаємо запит до FastAPI
    const apiResponse = await fetch(`${API_BASE_URL}/api/broadcasts/upload`, {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
      },
      body: formData,
    });

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${apiResponse.status}`);
    }

    const data = await apiResponse.json();

    return NextResponse.json({
      success: true,
      data: data,
    });

  } catch (error) {
    console.error('Broadcast upload API error:', error);
    
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Failed to upload file',
    }, { status: 500 });
  }
}
