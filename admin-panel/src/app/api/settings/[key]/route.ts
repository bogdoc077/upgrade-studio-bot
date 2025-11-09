import { NextResponse, NextRequest } from 'next/server';

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ key: string }> | { key: string } }
) {
  try {
    // Підтримка для різних версій Next.js
    const resolvedParams = context.params instanceof Promise ? await context.params : context.params;
    const settingKey = resolvedParams.key; // bot, stripe, subscription, webhook
    const authHeader = request.headers.get('authorization');
    const cookieToken = request.cookies.get('auth_token')?.value;
    const body = await request.json();



    // Спочатку пробуємо JWT токен з header або cookies
    let token = '';
    if (authHeader?.startsWith('Bearer ') && authHeader.length > 7) {
      const jwtToken = authHeader.replace('Bearer ', '').trim();
      if (jwtToken) {
        token = jwtToken;
      }
    } else if (cookieToken?.trim()) {
      token = cookieToken.trim();
    }

    // Якщо немає валідного JWT токена, використовуємо Basic Auth як fallback
    if (!token) {
      console.log('Немає JWT токена, використовую Basic Auth fallback');
      const username = process.env.ADMIN_USERNAME || 'admin';
      const password = process.env.ADMIN_PASSWORD || 'Qwerty21';
      const basicAuth = Buffer.from(`${username}:${password}`).toString('base64');
      token = `Basic_${basicAuth}`; // Маркер для Basic Auth
    } else {
      console.log('Використовую JWT токен:', token.substring(0, 10) + '...');
    }

    if (!settingKey || settingKey.trim() === '') {
      return NextResponse.json({
        success: false,
        error: 'Setting key is required'
      }, { status: 400 });
    }

    // Мапимо дані frontend-у до конкретних налаштувань для кожного блоку
    const settingMappings: { [key: string]: { [field: string]: { key: string, category: string, is_sensitive?: boolean } } } = {
      bot: {
        bot_token: { key: 'bot_token', category: 'bot', is_sensitive: true }
      },
      stripe: {
        public_key: { key: 'stripe_publishable_key', category: 'payment', is_sensitive: false },
        secret_key: { key: 'stripe_secret_key', category: 'payment', is_sensitive: true },
        webhook_endpoint: { key: 'stripe_webhook_secret', category: 'payment', is_sensitive: true }
      },
      subscription: {
        monthly_price: { key: 'subscription_price', category: 'payment', is_sensitive: false }
      },
      webhook: {
        url: { key: 'webhook_url', category: 'bot', is_sensitive: false }
      }
    };

    const sectionMappings = settingMappings[settingKey];
    if (!sectionMappings) {
      return NextResponse.json({
        success: false,
        error: `Unknown setting section: ${settingKey}`
      }, { status: 400 });
    }

    // Оновлюємо кожне налаштування в секції
    let hasErrors = false;
    const results = [];

    for (const [fieldName, fieldValue] of Object.entries(body)) {
      const mapping = sectionMappings[fieldName];
      if (!mapping) {
        continue; // Пропускаємо невідомі поля (наприклад, is_active)
      }

      let processedValue: string | number = fieldValue as any;
      
      // Ціна підписки зберігається як число в євро (без конвертації)
      if (mapping.key === 'subscription_price' && typeof fieldValue === 'number') {
        processedValue = fieldValue; // зберігаємо як є в євро
      }

      const settingData = {
        key: mapping.key,
        value: processedValue.toString(),
        value_type: mapping.key === 'subscription_price' ? 'float' : (typeof processedValue === 'number' ? 'integer' : 'string'),
        category: mapping.category,
        is_sensitive: mapping.is_sensitive || false
      };



      try {
        // Визначаємо тип авторизації
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };

        if (token.startsWith('Basic_')) {
          // Використовуємо Basic Auth
          headers['Authorization'] = `Basic ${token.substring(6)}`;
        } else {
          // Використовуємо JWT токен
          headers['Authorization'] = `Bearer ${token}`;
        }

        // Прямий запит до FastAPI
        const apiResponse = await fetch(`http://localhost:8000/api/settings/${mapping.key}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify(settingData)
        });

        if (!apiResponse.ok) {
          let errorMessage = `FastAPI error: ${apiResponse.status}`;
          try {
            const errorData = await apiResponse.json();
            errorMessage = errorData.detail || errorMessage;
          } catch (parseError) {
            // Якщо не вдається парсити JSON помилки, використовуємо статус
            const textError = await apiResponse.text().catch(() => '');
            errorMessage = textError || errorMessage;
          }
          hasErrors = true;
          results.push({ field: fieldName, error: errorMessage });
        } else {
          const responseData = await apiResponse.json().catch(() => ({}));
          results.push({ field: fieldName, success: true });
        }
      } catch (error) {
        hasErrors = true;
        results.push({ field: fieldName, error: error instanceof Error ? error.message : 'Unknown error' });
      }
    }

    if (hasErrors) {
      return NextResponse.json({
        success: false,
        error: 'Some settings failed to update',
        results
      }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      message: 'Settings updated successfully',
      results
    });

  } catch (error) {
    console.error('Update setting error:', error);
    
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    }, { status: 500 });
  }
}