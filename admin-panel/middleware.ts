import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Маршрути які не потребують авторизації
const publicPaths = ['/login']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  // Перевіряємо наявність токена в cookies
  const token = request.cookies.get('auth_token')?.value
  
  // Якщо користувач на сторінці логіну і має токен - перенаправляємо на дашборд
  if (pathname === '/login' && token) {
    return NextResponse.redirect(new URL('/', request.url))
  }
  
  // Перевіряємо чи це публічний маршрут
  if (publicPaths.includes(pathname)) {
    return NextResponse.next()
  }
  
  // Якщо немає токена, перенаправляємо на логін
  if (!token) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - logo.svg (logo file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|logo.svg).*)',
  ],
}