import os
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from app import db
from app.models.monitor_template import MonitorTemplate, MonitorCategory


class MonitorTemplateService:
    _instance = None
    _templates_cache: Dict[str, Dict[str, Any]] = {}
    _categories_cache: Dict[str, Dict[str, Any]] = {}
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, template_dir: str = None):
        if self._initialized:
            return
        
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates')
        
        self._template_dir = template_dir
        self.load_templates_from_db()
        self.load_categories_from_db()
        self._initialized = True
    
    def load_templates_from_db(self):
        templates = MonitorTemplate.query.all()
        for template in templates:
            self._templates_cache[template.app] = {
                'id': template.id,
                'app': template.app,
                'name': template.name,
                'category': template.category,
                'content': template.content,
                'version': template.version,
                'is_hidden': template.is_hidden
            }
    
    def load_categories_from_db(self):
        categories = MonitorCategory.query.all()
        for category in categories:
            self._categories_cache[category.code] = {
                'id': category.id,
                'name': category.name,
                'code': category.code,
                'icon': category.icon,
                'sort_order': category.sort_order,
                'parent_id': category.parent_id
            }
    
    def reload_templates(self):
        self._templates_cache.clear()
        self.load_templates_from_db()
    
    def reload_categories(self):
        self._categories_cache.clear()
        self.load_categories_from_db()
    
    def get_template(self, app: str) -> Optional[Dict[str, Any]]:
        return self._templates_cache.get(app)
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        return list(self._templates_cache.values())
    
    def get_templates_by_category(self, category: str) -> List[Dict[str, Any]]:
        return [t for t in self._templates_cache.values() if t.get('category') == category]
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        return list(self._categories_cache.values())
    
    def save_template(self, app: str, name: str, category: str, content: str) -> Dict[str, Any]:
        existing = MonitorTemplate.query.filter_by(app=app).first()
        
        if existing:
            existing.name = name
            existing.category = category
            existing.content = content
            existing.version = existing.version + 1
            db.session.commit()
            template_data = {
                'id': existing.id,
                'app': existing.app,
                'name': existing.name,
                'category': existing.category,
                'content': existing.content,
                'version': existing.version,
                'is_hidden': existing.is_hidden
            }
        else:
            template = MonitorTemplate(app=app, name=name, category=category, content=content)
            db.session.add(template)
            db.session.commit()
            template_data = {
                'id': template.id,
                'app': template.app,
                'name': template.name,
                'category': template.category,
                'content': template.content,
                'version': template.version,
                'is_hidden': template.is_hidden
            }
        
        self._templates_cache[app] = template_data
        return template_data
    
    def delete_template(self, app: str) -> bool:
        template = MonitorTemplate.query.filter_by(app=app).first()
        if template:
            db.session.delete(template)
            db.session.commit()
            if app in self._templates_cache:
                del self._templates_cache[app]
            return True
        return False
    
    def save_category(self, name: str, code: str, icon: str = None, parent_id: int = None) -> Dict[str, Any]:
        existing = MonitorCategory.query.filter_by(code=code).first()
        
        if existing:
            existing.name = name
            existing.icon = icon
            db.session.commit()
            category_data = {
                'id': existing.id,
                'name': existing.name,
                'code': existing.code,
                'icon': existing.icon,
                'sort_order': existing.sort_order,
                'parent_id': existing.parent_id
            }
        else:
            category = MonitorCategory(name=name, code=code, icon=icon, parent_id=parent_id)
            db.session.add(category)
            db.session.commit()
            category_data = {
                'id': category.id,
                'name': category.name,
                'code': category.code,
                'icon': category.icon,
                'sort_order': category.sort_order,
                'parent_id': category.parent_id
            }
        
        self._categories_cache[code] = category_data
        return category_data
    
    def delete_category(self, code: str) -> bool:
        category = MonitorCategory.query.filter_by(code=code).first()
        if category:
            db.session.delete(category)
            db.session.commit()
            if code in self._categories_cache:
                del self._categories_cache[code]
            return True
        return False
    
    def update_category(self, code: str, name: str, icon: str = None) -> Optional[Dict[str, Any]]:
        category = MonitorCategory.query.filter_by(code=code).first()
        if category:
            category.name = name
            if icon:
                category.icon = icon
            db.session.commit()
            category_data = {
                'id': category.id,
                'name': category.name,
                'code': category.code,
                'icon': category.icon,
                'sort_order': category.sort_order,
                'parent_id': category.parent_id
            }
            self._categories_cache[code] = category_data
            return category_data
        return None
    
    def parse_yaml_content(self, content: str) -> Optional[Dict[str, Any]]:
        try:
            result = {}
            
            # 解析 category
            cat_match = re.search(r'category:\s*(\w+)', content)
            if cat_match:
                result['category'] = cat_match.group(1)
            
            # 解析 name (多语言)
            name = {}
            zh_match = re.search(r'name:\s*\n\s*zh-CN:\s*([^\n]+)', content)
            en_match = re.search(r'name:\s*\n\s*en-US:\s*([^\n]+)', content)
            if zh_match:
                name['zh-CN'] = zh_match.group(1).strip()
            if en_match:
                name['en-US'] = en_match.group(1).strip()
            if name:
                result['name'] = name
            
            # 解析 app
            app_match = re.search(r'app:\s*(\w+)', content)
            if app_match:
                result['app'] = app_match.group(1)
            
            return result if result else None
        except Exception as e:
            print(f"YAML parsing error: {e}")
            return None
    
    def get_template_hierarchy(self, lang: str = 'zh-CN') -> List[Dict[str, Any]]:
        category_map = {}
        for cat in self._categories_cache.values():
            if cat['parent_id'] is None:
                category_map[cat['code']] = {
                    'code': cat['code'],
                    'name': cat['name'],
                    'icon': cat['icon'],
                    'children': []
                }
        
        for template in self._templates_cache.values():
            category = template.get('category')
            if category in category_map:
                parsed = self.parse_yaml_content(template.get('content', ''))
                template_name = parsed.get('name', {}).get(lang, template['app']) if parsed else template['app']
                category_map[category]['children'].append({
                    'app': template['app'],
                    'name': template_name,
                    'is_hidden': template.get('is_hidden', False)
                })
        
        return list(category_map.values())


template_service = MonitorTemplateService()
