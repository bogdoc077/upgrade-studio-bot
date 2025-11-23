import { NextResponse, NextRequest } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function GET(request: NextRequest) {
  try {
    // Отримуємо токен авторизації з заголовків
    const authHeader = request.headers.get('authorization');
    
    if (!authHeader) {
      return NextResponse.json(
        { success: false, error: 'Authorization required' },
        { status: 401 }
      );
    }

    // Робимо запит до FastAPI
    const url = `${API_BASE_URL}/api/users/export`;
    
    console.log('Making request to FastAPI users export:', url);
    
    const apiResponse = await fetch(url, {
      headers: {
        'Authorization': authHeader,
      },
    });

    console.log('FastAPI users export response status:', apiResponse.status);

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      console.log('FastAPI users export error:', errorData);
      throw new Error(errorData.detail || `HTTP ${apiResponse.status}`);
    }

    // Повертаємо файл
    const blob = await apiResponse.blob();
    const headers = new Headers();
    headers.set('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    headers.set('Content-Disposition', `attachment; filename="users_${new Date().toISOString().split('T')[0]}.xlsx"`);

    return new NextResponse(blob, {
      status: 200,
      headers,
    });

  } catch (error) {
    console.error('Users export API error:', error);
    
    return NextResponse.json({
      success: false,
      error: 'Failed to export users'
    }, { status: 500 });
  }
}
