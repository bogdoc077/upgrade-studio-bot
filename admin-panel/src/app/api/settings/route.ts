import { NextResponse, NextRequest } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

export async function GET(request: NextRequest) {
  try {
    // Отримання токена з cookies або заголовків
    const authHeader = request.headers.get('authorization');
    const cookieToken = request.cookies.get('auth_token')?.value;
    const token = authHeader?.replace('Bearer ', '') || cookieToken;

    let headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Спочатку спробуємо JWT токен, якщо є
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    } else {
      // Fallback на Basic Auth
      const username = process.env.ADMIN_USERNAME || 'admin';
      const password = process.env.ADMIN_PASSWORD || 'Qwerty21';
      const basicAuth = Buffer.from(`${username}:${password}`).toString('base64');
      headers['Authorization'] = `Basic ${basicAuth}`;
    }
    
    // Прямий запит до FastAPI з аутентифікацією
    const apiResponse = await fetch(`${API_BASE_URL}/api/settings`, {
      method: 'GET',
      headers,
    });

    if (!apiResponse.ok) {
      const errorText = await apiResponse.text();
      throw new Error(`FastAPI error: ${apiResponse.status} - ${errorText}`);
    }

    const fastApiData = await apiResponse.json();
    
    // Трансформуємо дані з FastAPI у формат для frontend
    const settingsData = {
      bot: {
        bot_token: fastApiData.bot_token || ""
      },
      stripe: {
        public_key: fastApiData.stripe_publishable_key || "",
        secret_key: fastApiData.stripe_secret_key || "",
        webhook_endpoint: fastApiData.stripe_webhook_secret || ""
      },
      subscription: {
        monthly_price: fastApiData.subscription_price || 15.00 // Ціна вже в євро
      },
      webhook: {
        url: fastApiData.webhook_url || ""
      }
    };

    return NextResponse.json({
      success: true,
      data: settingsData
    });

  } catch (error) {
    console.error('Settings API error:', error);
    
    // Fallback дані при помилці з'єднання з FastAPI
    const fallbackSettings = {
      bot: {
        bot_token: "",
        webhook_url: ""
      },
      stripe: {
        public_key: "",
        secret_key: "",
        webhook_endpoint: ""
      },
      subscription: {
        monthly_price: 15.00
      },
      webhook: {
        url: ""
      }
    };

    return NextResponse.json({
      success: true,
      data: fallbackSettings
    });
  }
}


