import { Directive, DirectiveBinding } from 'vue'
import { useUserStore } from '@/stores/user'

export const permission: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const userStore = useUserStore()
    const { value } = binding
    
    if (value && typeof value === 'string') {
      const hasPermission = userStore.hasPermission(value)
      if (!hasPermission) {
        el.parentNode?.removeChild(el)
      }
    } else if (value && Array.isArray(value)) {
      const hasPermission = value.some((permission: string) => 
        userStore.hasPermission(permission)
      )
      if (!hasPermission) {
        el.parentNode?.removeChild(el)
      }
    }
  }
}

export const role: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const userStore = useUserStore()
    const { value } = binding
    
    if (value && typeof value === 'string') {
      if (userStore.userInfo?.role !== value) {
        el.parentNode?.removeChild(el)
      }
    } else if (value && Array.isArray(value)) {
      const hasRole = value.includes(userStore.userInfo?.role || '')
      if (!hasRole) {
        el.parentNode?.removeChild(el)
      }
    }
  }
}

export default {
  permission,
  role
}
