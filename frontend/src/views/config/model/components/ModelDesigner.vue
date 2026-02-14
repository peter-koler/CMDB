<template>
  <a-drawer
    v-model:open="visible"
    :title="isEdit ? `编辑模型 - ${modelData.name}` : '创建模型'"
    width="100%"
    :destroy-on-close="true"
    @close="handleClose"
  >
    <template #extra>
      <a-space>
        <a-button @click="handleCancel">取消</a-button>
        <a-button @click="handlePreview">预览</a-button>
        <a-button type="primary" @click="handleSave" :loading="saving">保存</a-button>
      </a-space>
    </template>
    
    <div class="designer-container">
      <a-row :gutter="0" class="designer-main">
        <a-col :span="4" class="left-panel">
          <div class="panel-title">控件列表</div>
          <a-tabs v-model:activeKey="activeControlTab" class="control-tabs">
            <a-tab-pane key="basic" tab="基本控件">
              <div class="control-list">
                <div
                  v-for="control in basicControls"
                  :key="control.type"
                  class="control-item"
                  draggable="true"
                  @dragstart="handleDragStart($event, control)"
                >
                  <span class="control-icon">{{ control.icon }}</span>
                  <span class="control-name">{{ control.name }}</span>
                </div>
              </div>
            </a-tab-pane>
            <a-tab-pane key="layout" tab="布局控件">
              <div class="control-list">
                <div
                  v-for="control in layoutControls"
                  :key="control.type"
                  class="control-item"
                  draggable="true"
                  @dragstart="handleDragStart($event, control)"
                >
                  <span class="control-icon">{{ control.icon }}</span>
                  <span class="control-name">{{ control.name }}</span>
                </div>
              </div>
            </a-tab-pane>
          </a-tabs>
        </a-col>
        
        <a-col :span="14" class="center-panel">
          <div class="panel-title">
            画布区域
            <a-button size="small" type="link" @click="clearCanvas">清空画布</a-button>
          </div>
          <div
            class="canvas-area"
            @dragover.prevent
            @drop="handleDrop"
          >
            <div v-if="canvasItems.length === 0" class="canvas-empty">
              <InboxOutlined style="font-size: 48px; color: #ccc;" />
              <p>拖拽控件到此处</p>
            </div>
            
            <div v-else class="canvas-items">
              <a-row :gutter="16">
                <template v-for="(item, index) in canvasItems" :key="item.id">
                  <a-col :span="Number(item.props.span) || 24">
                    <div
                      v-if="item.controlType === 'group'"
                      class="canvas-group"
                      :class="{ selected: selectedItem?.id === item.id, 'drag-over': dragOverIndex === index }"
                      draggable="true"
                      @click="selectItem(item)"
                      @dragstart="handleCanvasDragStart($event, index)"
                      @dragover.prevent="handleCanvasDragOver($event, index)"
                      @dragleave="handleCanvasDragLeave"
                      @drop="handleCanvasDrop($event, index)"
                      @dragend="handleCanvasDragEnd"
                    >
                      <div class="group-header">
                        <HolderOutlined style="cursor: move; margin-right: 8px;" />
                        <span>{{ item.props.label }}</span>
                        <a-button type="text" size="small" danger @click.stop="removeItem(index)">
                          <DeleteOutlined />
                        </a-button>
                      </div>
                      <div class="group-content">
                    <div
                      v-for="(child, childIndex) in item.children"
                      :key="child.id"
                      class="canvas-field"
                      :class="{ selected: selectedItem?.id === child.id }"
                      @click.stop="selectItem(child)"
                    >
                      <div class="field-label">{{ child.props.label }}</div>
                      <div class="field-preview">
                        <template v-if="child.controlType === 'text'">
                          <a-input :placeholder="child.props.placeholder" disabled />
                        </template>
                        <template v-else-if="child.controlType === 'textarea'">
                          <a-input :placeholder="child.props.placeholder" disabled />
                        </template>
                        <template v-else-if="child.controlType === 'number'">
                          <a-input-number :placeholder="child.props.placeholder" disabled style="width: 100%" />
                        </template>
                        <template v-else-if="child.controlType === 'date'">
                          <a-date-picker :placeholder="child.props.placeholder" disabled style="width: 100%" />
                        </template>
                        <template v-else-if="child.controlType === 'select'">
                          <a-select :placeholder="child.props.placeholder" disabled style="width: 100%" />
                        </template>
                        <template v-else-if="child.controlType === 'radio'">
                          <a-radio-group disabled>
                            <a-radio v-for="opt in child.props.options" :key="opt.value" :value="opt.value">
                              {{ opt.label }}
                            </a-radio>
                          </a-radio-group>
                        </template>
                        <template v-else-if="child.controlType === 'checkbox'">
                          <a-checkbox-group disabled>
                            <a-checkbox v-for="opt in child.props.options" :key="opt.value" :value="opt.value">
                              {{ opt.label }}
                            </a-checkbox>
                          </a-checkbox-group>
                        </template>
                        <template v-else-if="child.controlType === 'switch'">
                          <a-switch disabled />
                        </template>
                        <template v-else-if="child.controlType === 'user'">
                          <a-select
                            mode="multiple"
                            :placeholder="child.props.placeholder"
                            disabled
                            style="width: 100%"
                          />
                        </template>
                        <template v-else-if="child.controlType === 'reference'">
                          <a-select :placeholder="child.props.placeholder" disabled style="width: 100%" />
                        </template>
                        <template v-else-if="child.controlType === 'image'">
                          <a-upload disabled>
                            <a-button>上传图片</a-button>
                          </a-upload>
                        </template>
                        <template v-else-if="child.controlType === 'file'">
                          <a-upload disabled>
                            <a-button>上传附件</a-button>
                          </a-upload>
                        </template>
                        <template v-else-if="child.controlType === 'numberRange'">
                          <a-input-group compact>
                            <a-input-number style="width: 45%" disabled />
                            <a-input style="width: 10%; text-align: center" disabled value="-" />
                            <a-input-number style="width: 45%" disabled />
                          </a-input-group>
                        </template>
                      </div>
                      <div class="field-actions">
                        <a-button type="text" size="small" @click.stop="moveItem(index, -1)" :disabled="childIndex === 0">
                          <UpOutlined />
                        </a-button>
                        <a-button type="text" size="small" @click.stop="moveItem(index, 1)" :disabled="childIndex === (item.children?.length || 0) - 1">
                          <DownOutlined />
                        </a-button>
                        <a-button type="text" size="small" danger @click.stop="removeChildItem(item, childIndex)">
                          <DeleteOutlined />
                        </a-button>
                      </div>
                    </div>
                    <div
                      v-if="item.props.allowDrop"
                      class="drop-hint"
                      @dragover.prevent
                      @drop="handleDropInGroup($event, item)"
                    >
                      拖拽控件到此处
                    </div>
                  </div>
                </div>
                
                <div
                  v-else
                  class="canvas-field"
                  :class="{ selected: selectedItem?.id === item.id, 'drag-over': dragOverIndex === index }"
                  draggable="true"
                  @click="selectItem(item)"
                  @dragstart="handleCanvasDragStart($event, index)"
                  @dragover.prevent="handleCanvasDragOver($event, index)"
                  @dragleave="handleCanvasDragLeave"
                  @drop="handleCanvasDrop($event, index)"
                  @dragend="handleCanvasDragEnd"
                >
                  <div class="field-label">
                    <HolderOutlined style="cursor: move; margin-right: 4px;" />
                    {{ item.props.label }}
                    <span v-if="item.props.required" class="required-mark">*</span>
                  </div>
                  <div class="field-preview">
                    <template v-if="item.controlType === 'text'">
                      <a-input :placeholder="item.props.placeholder" disabled />
                    </template>
                    <template v-else-if="item.controlType === 'textarea'">
                      <a-input :placeholder="item.props.placeholder" disabled />
                    </template>
                    <template v-else-if="item.controlType === 'number'">
                      <a-input-number :placeholder="item.props.placeholder" disabled style="width: 100%" />
                    </template>
                    <template v-else-if="item.controlType === 'date'">
                      <a-date-picker :placeholder="item.props.placeholder" disabled style="width: 100%" />
                    </template>
                    <template v-else-if="item.controlType === 'select'">
                      <a-select :placeholder="item.props.placeholder" disabled style="width: 100%" />
                    </template>
                    <template v-else-if="item.controlType === 'radio'">
                      <a-radio-group disabled>
                        <a-radio v-for="opt in item.props.options" :key="opt.value" :value="opt.value">
                          {{ opt.label }}
                        </a-radio>
                      </a-radio-group>
                    </template>
                    <template v-else-if="item.controlType === 'checkbox'">
                      <a-checkbox-group disabled>
                        <a-checkbox v-for="opt in item.props.options" :key="opt.value" :value="opt.value">
                          {{ opt.label }}
                        </a-checkbox>
                      </a-checkbox-group>
                    </template>
                    <template v-else-if="item.controlType === 'switch'">
                      <a-switch disabled />
                    </template>
                    <template v-else-if="item.controlType === 'user'">
                      <a-select
                        mode="multiple"
                        :placeholder="item.props.placeholder"
                        disabled
                        style="width: 100%"
                      />
                    </template>
                    <template v-else-if="item.controlType === 'reference'">
                      <a-select :placeholder="item.props.placeholder" disabled style="width: 100%" />
                    </template>
                    <template v-else-if="item.controlType === 'image'">
                      <a-upload disabled>
                        <a-button>上传图片</a-button>
                      </a-upload>
                    </template>
                    <template v-else-if="item.controlType === 'file'">
                      <a-upload disabled>
                        <a-button>上传附件</a-button>
                      </a-upload>
                    </template>
                    <template v-else-if="item.controlType === 'numberRange'">
                      <a-input-group compact>
                        <a-input-number style="width: 45%" disabled />
                        <a-input style="width: 10%; text-align: center" disabled value="-" />
                        <a-input-number style="width: 45%" disabled />
                      </a-input-group>
                    </template>
                    <template v-else-if="item.controlType === 'table'">
                      <a-table :columns="item.props.columns" :data-source="[]" size="small" />
                    </template>
                  </div>
                  <div class="field-actions">
                    <a-button type="text" size="small" @click.stop="moveItem(index, -1)" :disabled="index === 0">
                      <UpOutlined />
                    </a-button>
                    <a-button type="text" size="small" @click.stop="moveItem(index, 1)" :disabled="index === canvasItems.length - 1">
                      <DownOutlined />
                    </a-button>
                    <a-button type="text" size="small" danger @click.stop="removeItem(index)">
                      <DeleteOutlined />
                    </a-button>
                  </div>
                </div>
                  </a-col>
                </template>
              </a-row>
            </div>
          </div>
        </a-col>
        
        <a-col :span="6" class="right-panel">
          <div class="panel-title">属性配置</div>
          <div class="property-panel">
            <template v-if="selectedItem">
              <a-form :model="selectedItem.props" :label-col="{ span: 8 }" :wrapper-col="{ span: 16 }">
                <a-divider>基本属性</a-divider>
                
                <a-form-item label="字段标签" v-if="selectedItem.controlType !== 'group'">
                  <a-input v-model:value="selectedItem.props.label" />
                </a-form-item>
                
                <a-form-item label="分组标题" v-if="selectedItem.controlType === 'group'">
                  <a-input v-model:value="selectedItem.props.label" />
                </a-form-item>
                
                <a-form-item label="字段编码" v-if="selectedItem.controlType !== 'group'">
                  <a-input v-model:value="selectedItem.props.code" @change="handleCodeChange" />
                </a-form-item>
                
                <a-form-item label="占位符" v-if="showPlaceholder">
                  <a-input v-model:value="selectedItem.props.placeholder" />
                </a-form-item>
                
                <a-form-item label="默认值" v-if="showDefaultValue">
                  <a-input v-model:value="selectedItem.props.defaultValue" />
                </a-form-item>
                
                <a-form-item label="必填" v-if="selectedItem.controlType !== 'group'">
                  <a-switch v-model:checked="selectedItem.props.required" />
                </a-form-item>
                
                <a-form-item label="禁用" v-if="selectedItem.controlType !== 'group'">
                  <a-switch v-model:checked="selectedItem.props.disabled" />
                </a-form-item>
                
                <a-form-item label="占用列数" v-if="selectedItem.controlType !== 'group'">
                  <a-select v-model:value="selectedItem.props.span">
                    <a-select-option :value="24">整行 (100%)</a-select-option>
                    <a-select-option :value="12">1/2 行 (50%)</a-select-option>
                    <a-select-option :value="8">1/3 行 (33%)</a-select-option>
                    <a-select-option :value="6">1/4 行 (25%)</a-select-option>
                  </a-select>
                </a-form-item>
                
                <a-form-item label="显示长度" v-if="selectedItem.controlType === 'text'">
                  <a-input-number v-model:value="selectedItem.props.maxLength" :min="1" :max="500" />
                </a-form-item>
                
                <a-form-item label="行数" v-if="selectedItem.controlType === 'textarea'">
                  <a-input-number v-model:value="selectedItem.props.rows" :min="2" :max="20" />
                </a-form-item>
                
                <a-form-item label="最小值" v-if="selectedItem.controlType === 'number'">
                  <a-input-number v-model:value="selectedItem.props.min" style="width: 100%" />
                </a-form-item>
                
                <a-form-item label="最大值" v-if="selectedItem.controlType === 'number'">
                  <a-input-number v-model:value="selectedItem.props.max" style="width: 100%" />
                </a-form-item>
                
                <a-form-item label="日期格式" v-if="selectedItem.controlType === 'date'">
                  <a-select v-model:value="selectedItem.props.format">
                    <a-select-option value="YYYY-MM-DD">YYYY-MM-DD</a-select-option>
                    <a-select-option value="YYYY-MM-DD HH:mm:ss">YYYY-MM-DD HH:mm:ss</a-select-option>
                    <a-select-option value="YYYY-MM">YYYY-MM</a-select-option>
                    <a-select-option value="YYYY">YYYY</a-select-option>
                  </a-select>
                </a-form-item>
                
                <a-form-item label="选择模式" v-if="selectedItem.controlType === 'user'">
                  <a-select v-model:value="selectedItem.props.mode">
                    <a-select-option value="single">单选</a-select-option>
                    <a-select-option value="multiple">多选</a-select-option>
                  </a-select>
                </a-form-item>
                
                <a-form-item label="关联模型" v-if="selectedItem.controlType === 'reference'">
                  <a-select v-model:value="selectedItem.props.refModelId" :options="refModelOptions" />
                </a-form-item>
                
                <a-form-item label="允许拖入" v-if="selectedItem.controlType === 'group'">
                  <a-switch v-model:checked="selectedItem.props.allowDrop" />
                </a-form-item>
                
                <a-divider v-if="selectedItem.controlType === 'select' || selectedItem.controlType === 'radio' || selectedItem.controlType === 'checkbox'">选项配置</a-divider>
                
                <template v-if="selectedItem.controlType === 'select' || selectedItem.controlType === 'radio' || selectedItem.controlType === 'checkbox'">
                  <a-form-item label="选项类型">
                    <a-radio-group v-model:value="selectedItem.props.optionType">
                      <a-radio value="custom">自定义</a-radio>
                      <a-radio value="dynamic">动态加载</a-radio>
                    </a-radio-group>
                  </a-form-item>
                  
                  <template v-if="selectedItem.props.optionType === 'custom'">
                    <div class="options-editor">
                      <div v-for="(option, idx) in selectedItem.props.options" :key="idx" class="option-item">
                        <a-input v-model:value="option.label" placeholder="标签" style="width: 80px" />
                        <a-input v-model:value="option.value" placeholder="值" style="width: 60px" />
                        <a-button type="text" size="small" @click="removeOption(selectedItem.props.options, idx)">
                          <MinusCircleOutlined />
                        </a-button>
                      </div>
                      <a-button type="dashed" block @click="addOption(selectedItem.props.options)">
                        <PlusOutlined /> 添加选项
                      </a-button>
                    </div>
                  </template>
                </template>
                
                <a-divider v-if="selectedItem.controlType === 'table'">表格配置</a-divider>
                
                <template v-if="selectedItem.controlType === 'table'">
                  <a-form-item label="列数">
                    <a-input-number v-model:value="selectedItem.props.columnCount" :min="1" :max="10" />
                  </a-form-item>
                  <a-form-item label="允许编辑">
                    <a-switch v-model:checked="selectedItem.props.editable" />
                  </a-form-item>
                  <a-form-item label="允许新增">
                    <a-switch v-model:checked="selectedItem.props.addable" />
                  </a-form-item>
                  <a-form-item label="允许删除">
                    <a-switch v-model:checked="selectedItem.props.deletable" />
                  </a-form-item>
                </template>
                
                <a-divider>校验规则</a-divider>
                
                <a-form-item label="自定义校验">
                  <a-switch v-model:checked="selectedItem.props.customValidation" />
                </a-form-item>
                
                <a-form-item label="校验规则" v-if="selectedItem.props.customValidation">
                  <a-input v-model:value="selectedItem.props.validationRule" placeholder="正则表达式" />
                </a-form-item>
                
                <a-form-item label="错误提示" v-if="selectedItem.props.customValidation">
                  <a-input v-model:value="selectedItem.props.validationMessage" placeholder="校验失败提示" />
                </a-form-item>
                
                <a-divider>其他</a-divider>
                
                <a-form-item label="帮助文本">
                  <a-textarea v-model:value="selectedItem.props.helpText" :rows="2" />
                </a-form-item>
                
                <a-form-item label="字段描述">
                  <a-textarea v-model:value="selectedItem.props.description" :rows="2" />
                </a-form-item>
              </a-form>
            </template>
            <div v-else class="empty-property">
              <InboxOutlined style="font-size: 32px; color: #ccc;" />
              <p>请选择画布中的控件</p>
            </div>
          </div>
        </a-col>
      </a-row>
    </div>
    
    <a-modal
      v-model:open="basicModalVisible"
      title="基本信息"
      @ok="handleBasicSave"
      width="600px"
    >
      <a-form :model="modelData" :label-col="{ span: 4 }">
        <a-form-item label="模型名称" required>
          <a-input v-model:value="modelData.name" />
        </a-form-item>
        <a-form-item label="模型编码" required>
          <a-input v-model:value="modelData.code" :disabled="isEdit" />
        </a-form-item>
        <a-form-item label="模型类型">
          <a-select v-model:value="modelData.type_id" :options="typeOptions" />
        </a-form-item>
        <a-form-item label="模型图标">
          <a-input v-model:value="modelData.icon" />
        </a-form-item>
        <a-form-item label="模型描述">
          <a-textarea v-model:value="modelData.description" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
    
    <a-modal
      v-model:open="previewModalVisible"
      title="表单预览"
      width="800px"
      :footer="null"
    >
      <a-form :model="previewForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-row :gutter="16">
          <template v-for="item in canvasItems" :key="item.id">
            <a-col :span="Number(item.props.span) || 24">
              <a-form-item
                v-if="item.controlType !== 'group' && item.controlType !== 'table'"
                :label="item.props.label"
                :required="item.props.required"
              >
            <template v-if="item.controlType === 'text'">
              <a-input v-model:value="previewForm[item.props.code]" :placeholder="item.props.placeholder" />
            </template>
            <template v-else-if="item.controlType === 'textarea'">
              <a-textarea v-model:value="previewForm[item.props.code]" :placeholder="item.props.placeholder" :rows="item.props.rows" />
            </template>
            <template v-else-if="item.controlType === 'number'">
              <a-input-number v-model:value="previewForm[item.props.code]" :placeholder="item.props.placeholder" :min="item.props.min" :max="item.props.max" style="width: 100%" />
            </template>
            <template v-else-if="item.controlType === 'date'">
              <a-date-picker v-model:value="previewForm[item.props.code]" :placeholder="item.props.placeholder" :format="item.props.format" style="width: 100%" />
            </template>
            <template v-else-if="item.controlType === 'select'">
              <a-select v-model:value="previewForm[item.props.code]" :placeholder="item.props.placeholder" style="width: 100%">
                <a-select-option v-for="opt in item.props.options" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </a-select-option>
              </a-select>
            </template>
            <template v-else-if="item.controlType === 'radio'">
              <a-radio-group v-model:value="previewForm[item.props.code]">
                <a-radio v-for="opt in item.props.options" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </a-radio>
              </a-radio-group>
            </template>
            <template v-else-if="item.controlType === 'checkbox'">
              <a-checkbox-group v-model:value="previewForm[item.props.code]">
                <a-checkbox v-for="opt in item.props.options" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </a-checkbox>
              </a-checkbox-group>
            </template>
            <template v-else-if="item.controlType === 'switch'">
              <a-switch v-model:checked="previewForm[item.props.code]" />
            </template>
            <template v-else-if="item.controlType === 'user'">
              <a-select
                v-model:value="previewForm[item.props.code]"
                mode="multiple"
                :placeholder="item.props.placeholder"
                style="width: 100%"
              />
            </template>
            <template v-else-if="item.controlType === 'reference'">
              <a-select v-model:value="previewForm[item.props.code]" :placeholder="item.props.placeholder" style="width: 100%">
              </a-select>
            </template>
            <template v-else-if="item.controlType === 'image'">
              <a-upload>
                <a-button>
                  <UploadOutlined /> 上传图片
                </a-button>
              </a-upload>
            </template>
            <template v-else-if="item.controlType === 'file'">
              <a-upload>
                <a-button>
                  <UploadOutlined /> 上传附件
                </a-button>
              </a-upload>
            </template>
            <template v-else-if="item.controlType === 'numberRange'">
              <a-input-group compact>
                <a-input-number v-model:value="previewForm[item.props.code + '_min']" style="width: 45%" />
                <a-input style="width: 10%; text-align: center" value="-" disabled />
                <a-input-number v-model:value="previewForm[item.props.code + '_max']" style="width: 45%" />
              </a-input-group>
            </template>
            <div v-if="item.props.helpText" class="help-text">{{ item.props.helpText }}</div>
          </a-form-item>
          
          <div v-else-if="item.controlType === 'group'" class="preview-group">
            <div class="group-title">{{ item.props.label }}</div>
            <a-form-item
              v-for="child in item.children"
              :key="child.id"
              :label="child.props.label"
              :required="child.props.required"
            >
              <template v-if="child.controlType === 'text'">
                <a-input v-model:value="previewForm[child.props.code]" :placeholder="child.props.placeholder" />
              </template>
              <template v-else-if="child.controlType === 'textarea'">
                <a-textarea v-model:value="previewForm[child.props.code]" :placeholder="child.props.placeholder" :rows="child.props.rows" />
              </template>
              <template v-else-if="child.controlType === 'number'">
                <a-input-number v-model:value="previewForm[child.props.code]" :placeholder="child.props.placeholder" style="width: 100%" />
              </template>
              <template v-else-if="child.controlType === 'date'">
                <a-date-picker v-model:value="previewForm[child.props.code]" :placeholder="child.props.placeholder" style="width: 100%" />
              </template>
              <template v-else-if="child.controlType === 'select'">
                <a-select v-model:value="previewForm[child.props.code]" :placeholder="child.props.placeholder" style="width: 100%">
                  <a-select-option v-for="opt in child.props.options" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </a-select-option>
                </a-select>
              </template>
              <template v-else-if="child.controlType === 'radio'">
                <a-radio-group v-model:value="previewForm[child.props.code]">
                  <a-radio v-for="opt in child.props.options" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </a-radio>
                </a-radio-group>
              </template>
              <template v-else-if="child.controlType === 'checkbox'">
                <a-checkbox-group v-model:value="previewForm[child.props.code]">
                  <a-checkbox v-for="opt in child.props.options" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </a-checkbox>
                </a-checkbox-group>
              </template>
              <template v-else-if="child.controlType === 'switch'">
                <a-switch v-model:checked="previewForm[child.props.code]" />
              </template>
              <div v-if="child.props.helpText" class="help-text">{{ child.props.helpText }}</div>
            </a-form-item>
          </div>
            </a-col>
          </template>
        </a-row>
      </a-form>
    </a-modal>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  DeleteOutlined,
  UpOutlined,
  DownOutlined,
  InboxOutlined,
  MinusCircleOutlined,
  UploadOutlined,
  HolderOutlined
} from '@ant-design/icons-vue'
import { getModelTypes, getModels } from '@/api/cmdb'

interface CanvasItem {
  id: string
  controlType: string
  props: Record<string, any>
  children?: CanvasItem[]
}

const props = defineProps<{
  model?: any
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'save', data: any): void
}>()

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const isEdit = computed(() => !!props.model)
const saving = ref(false)
const activeControlTab = ref('basic')
const canvasItems = ref<CanvasItem[]>([])
const selectedItem = ref<CanvasItem | null>(null)
const draggedIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)
const previewForm = ref<Record<string, any>>({})

const basicModalVisible = ref(false)
const previewModalVisible = ref(false)

const modelData = ref({
  id: null as number | null,
  name: '',
  code: '',
  type_id: null as number | null,
  icon: 'AppstoreOutlined',
  description: ''
})

const typeOptions = ref<{label: string, value: number}[]>([])
const refModelOptions = ref<{label: string, value: number}[]>([])

const basicControls = [
  { type: 'text', name: '单行文本', icon: 'T' },
  { type: 'textarea', name: '多行文本', icon: '📝' },
  { type: 'number', name: '数字', icon: '#' },
  { type: 'numberRange', name: '数字范围', icon: '⬌' },
  { type: 'date', name: '日期', icon: '📅' },
  { type: 'select', name: '下拉选择', icon: '▼' },
  { type: 'radio', name: '单选', icon: '◯' },
  { type: 'checkbox', name: '多选', icon: '☐' },
  { type: 'switch', name: '开关', icon: 'S' },
  { type: 'user', name: '人员', icon: '👤' },
  { type: 'reference', name: '引用', icon: '🔗' },
  { type: 'image', name: '图片', icon: '🖼' },
  { type: 'file', name: '附件', icon: '📎' }
]

const layoutControls = [
  { type: 'group', name: '属性分组', icon: '📁' },
  { type: 'table', name: '表格', icon: '▦' }
]

const showPlaceholder = computed(() => {
  if (!selectedItem.value) return false
  return ['text', 'textarea', 'number', 'date', 'select', 'user', 'reference'].includes(selectedItem.value.controlType)
})

const showDefaultValue = computed(() => {
  if (!selectedItem.value) return false
  return ['text', 'textarea', 'number', 'select'].includes(selectedItem.value.controlType)
})

watch(() => props.visible, (val) => {
  if (val) {
    if (props.model) {
      modelData.value = { ...props.model }
      if (props.model.form_config) {
        try {
          canvasItems.value = JSON.parse(props.model.form_config)
        } catch {
          canvasItems.value = []
        }
      } else {
        canvasItems.value = []
      }
    } else {
      modelData.value = {
        id: null,
        name: '',
        code: '',
        type_id: null,
        icon: 'AppstoreOutlined',
        description: ''
      }
      canvasItems.value = []
    }
    selectedItem.value = null
    loadModelTypes()
    loadRefModels()
  }
})

const loadModelTypes = async () => {
  try {
    const res = await getModelTypes()
    if (res.code === 200) {
      typeOptions.value = res.data.map((item: any) => ({
        label: item.name,
        value: item.id
      }))
    }
  } catch (e) {
    console.error(e)
  }
}

const loadRefModels = async () => {
  try {
    const res = await getModels({ per_page: 100 })
    if (res.code === 200) {
      refModelOptions.value = (res.data.items || res.data || []).map((item: any) => ({
        label: item.name,
        value: item.id
      }))
    }
  } catch (e) {
    console.error(e)
  }
}

let itemIdCounter = 1
const generateId = () => `item_${itemIdCounter++}`

const defaultProps: Record<string, Record<string, any>> = {
  text: { label: '单行文本', code: '', placeholder: '请输入', required: false, disabled: false, maxLength: 100, helpText: '', description: '', customValidation: false, span: 24 },
  textarea: { label: '多行文本', code: '', placeholder: '请输入', required: false, disabled: false, rows: 4, helpText: '', description: '', customValidation: false, span: 24 },
  number: { label: '数字', code: '', placeholder: '请输入', required: false, disabled: false, min: undefined, max: undefined, helpText: '', description: '', customValidation: false, span: 24 },
  numberRange: { label: '数字范围', code: '', placeholder: '请输入', required: false, disabled: false, helpText: '', description: '', customValidation: false, span: 24 },
  date: { label: '日期', code: '', placeholder: '请选择', required: false, disabled: false, format: 'YYYY-MM-DD', helpText: '', description: '', customValidation: false, span: 24 },
  select: { label: '下拉选择', code: '', placeholder: '请选择', required: false, disabled: false, optionType: 'custom', options: [{ label: '选项1', value: 'option1' }], helpText: '', description: '', customValidation: false, span: 24 },
  radio: { label: '单选', code: '', required: false, disabled: false, optionType: 'custom', options: [{ label: '选项1', value: 'option1' }], helpText: '', description: '', customValidation: false, span: 24 },
  checkbox: { label: '多选', code: '', required: false, disabled: false, optionType: 'custom', options: [{ label: '选项1', value: 'option1' }], helpText: '', description: '', customValidation: false, span: 24 },
  switch: { label: '开关', code: '', required: false, disabled: false, defaultValue: false, helpText: '', description: '', customValidation: false, span: 24 },
  user: { label: '人员', code: '', placeholder: '请选择', required: false, disabled: false, mode: 'multiple', helpText: '', description: '', customValidation: false, span: 24 },
  reference: { label: '引用', code: '', placeholder: '请选择', required: false, disabled: false, refModelId: undefined, helpText: '', description: '', customValidation: false, span: 24 },
  image: { label: '图片', code: '', required: false, disabled: false, maxCount: 1, helpText: '', description: '', customValidation: false, span: 24 },
  file: { label: '附件', code: '', required: false, disabled: false, maxCount: 1, helpText: '', description: '', customValidation: false, span: 24 },
  group: { label: '分组标题', allowDrop: true, span: 24 },
  table: { label: '表格', code: '', columns: 3, editable: true, addable: true, deletable: true, helpText: '', description: '', span: 24 }
}

const handleDragStart = (event: DragEvent, control: any) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('controlType', control.type)
  }
}

const handleDrop = (event: DragEvent) => {
  const controlType = event.dataTransfer?.getData('controlType')
  if (!controlType) return
  
  const newItem: CanvasItem = {
    id: generateId(),
    controlType,
    props: { ...defaultProps[controlType] }
  }
  
  if (controlType === 'group') {
    newItem.children = []
  }
  
  canvasItems.value.push(newItem)
  selectedItem.value = newItem
}

const handleDropInGroup = (event: DragEvent, group: CanvasItem) => {
  const controlType = event.dataTransfer?.getData('controlType')
  if (!controlType || controlType === 'group' || controlType === 'table') return
  
  const newItem: CanvasItem = {
    id: generateId(),
    controlType,
    props: { ...defaultProps[controlType] }
  }
  
  if (!group.children) {
    group.children = []
  }
  group.children.push(newItem)
}

const handleCanvasDragStart = (event: DragEvent, index: number) => {
  draggedIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

const handleCanvasDragOver = (event: DragEvent, index: number) => {
  event.preventDefault()
  dragOverIndex.value = index
}

const handleCanvasDragLeave = () => {
  dragOverIndex.value = null
}

const handleCanvasDrop = (event: DragEvent, targetIndex: number) => {
  event.preventDefault()
  if (draggedIndex.value === null || draggedIndex.value === targetIndex) {
    dragOverIndex.value = null
    draggedIndex.value = null
    return
  }
  
  const items = canvasItems.value
  const draggedItem = items[draggedIndex.value]
  items.splice(draggedIndex.value, 1)
  items.splice(targetIndex, 0, draggedItem)
  
  dragOverIndex.value = null
  draggedIndex.value = null
}

const handleCanvasDragEnd = () => {
  dragOverIndex.value = null
  draggedIndex.value = null
}

const selectItem = (item: CanvasItem) => {
  selectedItem.value = item
}

const removeItem = (index: number) => {
  canvasItems.value.splice(index, 1)
  if (selectedItem.value && canvasItems.value.indexOf(selectedItem.value) === -1) {
    selectedItem.value = null
  }
}

const removeChildItem = (group: CanvasItem, index: number) => {
  if (group.children) {
    group.children.splice(index, 1)
  }
}

const moveItem = (index: number, direction: number) => {
  const newIndex = index + direction
  if (newIndex < 0 || newIndex >= canvasItems.value.length) return
  
  const temp = canvasItems.value[index]
  canvasItems.value[index] = canvasItems.value[newIndex]
  canvasItems.value[newIndex] = temp
}

const clearCanvas = () => {
  canvasItems.value = []
  selectedItem.value = null
}

const addOption = (options: any[]) => {
  options.push({ label: `选项${options.length + 1}`, value: `option${options.length + 1}` })
}

const removeOption = (options: any[], index: number) => {
  options.splice(index, 1)
}

const handleCodeChange = () => {
  // 可以在这里添加编码格式验证
}

const handleClose = () => {
  visible.value = false
}

const handleCancel = () => {
  visible.value = false
}

const handleBasicSave = () => {
  basicModalVisible.value = false
}

const handlePreview = () => {
  previewForm.value = {}
  canvasItems.value.forEach(item => {
    if (item.controlType === 'group' && item.children) {
      item.children.forEach(child => {
        previewForm.value[child.props.code] = child.props.defaultValue || undefined
      })
    } else if (item.controlType !== 'table') {
      previewForm.value[item.props.code] = item.props.defaultValue || undefined
    }
  })
  previewModalVisible.value = true
}

const handleSave = async () => {
  if (!modelData.value.name) {
    message.error('请输入模型名称')
    return
  }
  if (!modelData.value.code) {
    message.error('请输入模型编码')
    return
  }
  
  const hasDuplicateCode = canvasItems.value.some(item => {
    if (item.controlType === 'group' && item.children) {
      return item.children.some(child => !child.props.code)
    }
    return !item.props.code
  })
  
  if (hasDuplicateCode) {
    message.error('请完善所有字段的编码')
    return
  }
  
  saving.value = true
  try {
    emit('save', {
      ...modelData.value,
      form_config: JSON.stringify(canvasItems.value)
    })
    message.success('保存成功')
    visible.value = false
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.designer-container {
  height: calc(100vh - 200px);
  min-height: 500px;
  display: flex;
  flex-direction: column;
}

.designer-main {
  flex: 1;
  height: 100%;
}

.left-panel, .center-panel, .right-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #f0f0f0;
}

.left-panel {
  background: #fafafa;
}

.right-panel {
  border-right: none;
  background: #fafafa;
}

.panel-title {
  padding: 12px 16px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  background: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-tabs {
  flex: 1;
  overflow: auto;
}

.control-tabs :deep(.ant-tabs-content) {
  height: calc(100% - 46px);
  overflow: auto;
}

.control-list {
  padding: 8px;
}

.control-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  cursor: grab;
  transition: all 0.2s;
}

.control-item:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.control-item:active {
  cursor: grabbing;
}

.control-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e6f7ff;
  border-radius: 4px;
  margin-right: 8px;
  font-size: 12px;
}

.control-name {
  flex: 1;
  font-size: 13px;
}

.center-panel {
  background: #f5f5f5;
}

.canvas-area {
  flex: 1;
  padding: 16px;
  overflow: auto;
  background: #fff;
  min-height: 400px;
}

.canvas-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
  border: 2px dashed #ddd;
  border-radius: 8px;
}

.canvas-items {
  min-height: 100%;
}

.canvas-field {
  position: relative;
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid transparent;
  border-radius: 4px;
  transition: all 0.2s;
}

.canvas-field:hover {
  border-color: #d9d9d9;
}

.canvas-field.selected {
  border-color: #1890ff;
  background: #e6f7ff;
}

.canvas-field.drag-over {
  border-color: #1890ff;
  background: #e6f7ff;
  transform: scale(1.02);
}

.canvas-group.drag-over {
  border-color: #1890ff;
  background: #e6f7ff;
}

.field-label {
  margin-bottom: 8px;
  font-weight: 500;
  font-size: 13px;
}

.required-mark {
  color: #ff4d4f;
  margin-left: 4px;
}

.field-preview {
  pointer-events: none;
}

.field-actions {
  position: absolute;
  right: 8px;
  top: 8px;
  display: none;
}

.canvas-field:hover .field-actions {
  display: flex;
}

.canvas-group {
  margin-bottom: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}

.canvas-group.selected {
  border-color: #1890ff;
}

.group-header {
  padding: 8px 12px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.group-content {
  padding: 8px;
}

.drop-hint {
  padding: 16px;
  text-align: center;
  border: 1px dashed #ddd;
  border-radius: 4px;
  color: #999;
  margin-top: 8px;
}

.property-panel {
  flex: 1;
  padding: 16px;
  overflow: auto;
}

.empty-property {
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
}

.options-editor {
  padding: 8px;
  background: #fafafa;
  border-radius: 4px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.preview-group {
  padding: 16px;
  background: #fafafa;
  border-radius: 4px;
  margin-bottom: 16px;
}

.preview-group .group-title {
  font-weight: 600;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e8e8e8;
}

.help-text {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>
