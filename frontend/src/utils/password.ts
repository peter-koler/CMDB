import { getConfigs } from '@/api/config'

interface PasswordPolicy {
  minLength: number
  requireUppercase: boolean
  requireLowercase: boolean
  requireDigit: boolean
  requireSpecial: boolean
}

let cachedPolicy: PasswordPolicy | null = null

export async function getPasswordPolicy(): Promise<PasswordPolicy> {
  if (cachedPolicy) {
    return cachedPolicy
  }
  
  try {
    const res = await getConfigs()
    if (res.code === 200 && res.data) {
      cachedPolicy = {
        minLength: parseInt(res.data.password_min_length?.value || '8'),
        requireUppercase: res.data.require_uppercase?.value === 'true',
        requireLowercase: res.data.require_lowercase?.value === 'true',
        requireDigit: res.data.require_digit?.value === 'true',
        requireSpecial: res.data.require_special?.value === 'true'
      }
      return cachedPolicy
    }
  } catch (e) {
    console.error('Failed to get password policy:', e)
  }
  
  return {
    minLength: 8,
    requireUppercase: false,
    requireLowercase: false,
    requireDigit: false,
    requireSpecial: false
  }
}

export function validatePassword(password: string, policy?: PasswordPolicy): { valid: boolean; message: string } {
  const p = policy || {
    minLength: 8,
    requireUppercase: false,
    requireLowercase: false,
    requireDigit: false,
    requireSpecial: false
  }
  
  if (!password) {
    return { valid: false, message: '密码不能为空' }
  }
  
  if (password.length < p.minLength) {
    return { valid: false, message: `密码长度至少${p.minLength}位` }
  }
  
  if (p.requireUppercase && !/[A-Z]/.test(password)) {
    return { valid: false, message: '密码必须包含大写字母' }
  }
  
  if (p.requireLowercase && !/[a-z]/.test(password)) {
    return { valid: false, message: '密码必须包含小写字母' }
  }
  
  if (p.requireDigit && !/[0-9]/.test(password)) {
    return { valid: false, message: '密码必须包含数字' }
  }
  
  if (p.requireSpecial && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    return { valid: false, message: '密码必须包含特殊字符' }
  }
  
  return { valid: true, message: '密码符合要求' }
}

export function getPasswordStrength(password: string): number {
  if (!password) return 0
  
  let strength = 0
  if (password.length >= 8) strength += 20
  if (password.length >= 12) strength += 10
  if (/[a-z]/.test(password)) strength += 15
  if (/[A-Z]/.test(password)) strength += 15
  if (/[0-9]/.test(password)) strength += 20
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength += 20
  
  return Math.min(100, strength)
}

export function clearPasswordPolicyCache() {
  cachedPolicy = null
}
