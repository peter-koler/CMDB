export interface ParsedFormField {
  id: string
  code: string
  name: string
  field_type: string
  control_type: string
  required: boolean
  is_required: boolean
  default_value: any
  placeholder: string
  span: number
  sort_order: number
  field_order: number
  mode?: string
  option_type?: string
  dictionary_code?: string
  options: Array<{ label: string; value: any }>
  user_ids?: number[]
  reference_model_id?: number
  group_id: string
  group_label: string
  group_order: number
  help_text?: string
  helpText?: string
  description?: string
  format?: string
}

export const parseFormConfig = (value: any): any[] => {
  let parsed = value
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed)
    } catch {
      return []
    }
  }
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed)
    } catch {
      return []
    }
  }
  return Array.isArray(parsed) ? parsed : []
}

export const mapControlTypeToFieldType = (controlType: string): string => {
  const typeMap: Record<string, string> = {
    text: 'text',
    textarea: 'text',
    number: 'number',
    numberRange: 'numberRange',
    date: 'date',
    datetime: 'datetime',
    select: 'select',
    dropdown: 'dropdown',
    radio: 'select',
    checkbox: 'multiselect',
    cascade: 'cascade',
    switch: 'boolean',
    user: 'user',
    reference: 'reference',
    image: 'image',
    file: 'file',
    richtext: 'richtext'
  }
  return typeMap[controlType] || 'text'
}

export const normalizeOptions = (rawOptions: any): Array<{ label: string; value: any }> => {
  if (!Array.isArray(rawOptions)) return []
  return rawOptions
    .filter((item) => item && typeof item === 'object')
    .map((item) => ({
      label: item.label ?? item.value ?? '',
      value: item.value ?? item.label ?? ''
    }))
}

export const extractFieldsFromFormConfig = (formConfig: any): ParsedFormField[] => {
  const fields: ParsedFormField[] = []
  const parsed = parseFormConfig(formConfig)

  const walk = (items: any[], groupMeta?: { id: string; label: string; order: number }) => {
    items.forEach((item: any, index: number) => {
      if (!item || typeof item !== 'object') return
      if (item.controlType === 'group' && Array.isArray(item.children)) {
        walk(item.children, {
          id: item.id || `group_${index}`,
          label: item.props?.label || '属性分组',
          order: Number(item.props?.sortOrder ?? index)
        })
        return
      }

      const props = item.props || {}
      if (!props.code) return

      fields.push({
        id: item.id || `field_${index}_${props.code}`,
        code: props.code,
        name: props.label || props.code,
        field_type: mapControlTypeToFieldType(item.controlType),
        control_type: item.controlType,
        required: Boolean(props.required),
        is_required: Boolean(props.required),
        default_value: props.defaultValue,
        placeholder: props.placeholder || '',
        span: Number(props.span) || 12,
        sort_order: Number(props.sortOrder ?? index),
        field_order: Number(props.sortOrder ?? index),
        mode: props.mode || 'multiple',
        option_type: props.optionType || 'custom',
        dictionary_code: props.dictionaryCode || '',
        options: normalizeOptions(props.options),
        user_ids: Array.isArray(props.userIds) ? props.userIds : [],
        reference_model_id: props.refModelId,
        group_id: groupMeta?.id || '__base__',
        group_label: groupMeta?.label || '基础属性',
        group_order: groupMeta?.order ?? -1,
        help_text: props.helpText || '',
        helpText: props.helpText || '',
        description: props.description || '',
        format: props.format
      })
    })
  }

  walk(parsed)
  return fields
}
