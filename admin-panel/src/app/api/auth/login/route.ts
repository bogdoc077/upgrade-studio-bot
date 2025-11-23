import { NextRequest, NextResponse } from 'next/server'

const API_BASE_URL = process.env.API_INTERNAL_URL || 'http://localhost:8001'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { username, password } = body

    console.log(`[Login] Attempting login for user: ${username}`)
    console.log(`[Login] API_BASE_URL: ${API_BASE_URL}`)

    // Робимо запит до нашого API сервера
    const apiResponse = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    })

    console.log(`[Login] FastAPI response status: ${apiResponse.status}`)
    console.log(`[Login] FastAPI response headers:`, Object.fromEntries(apiResponse.headers.entries()))

    if (!apiResponse.ok) {
      const errorText = await apiResponse.text()
      console.error(`[Login] FastAPI error response:`, errorText)
      let errorData
      try {
        errorData = JSON.parse(errorText)
      } catch {
        errorData = { detail: 'Invalid response from API server' }
      }
      return NextResponse.json(
        { detail: errorData.detail || 'Authentication failed' },
        { status: apiResponse.status }
      )
    }

    const data = await apiResponse.json()
    console.log(`[Login] Login successful for user: ${username}`)
    
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