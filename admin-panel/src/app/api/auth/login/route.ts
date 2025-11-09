import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { username, password } = body

    // Робимо запит до нашого API сервера
    const apiResponse = await fetch('http://localhost:8000/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    })

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json()
      return NextResponse.json(
        { detail: errorData.detail || 'Authentication failed' },
        { status: apiResponse.status }
      )
    }

    const data = await apiResponse.json()
    
    // Створюємо відповідь з cookie
    const response = NextResponse.json(data)
    
    // Встановлюємо cookie з токеном
    response.cookies.set('auth_token', data.access_token, {
      httpOnly: false, // Дозволяємо JavaScript доступ
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 24 * 60 * 60, // 24 години
      path: '/',
    })

    return response
  } catch (error) {
    console.error('Login API error:', error)
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }
}