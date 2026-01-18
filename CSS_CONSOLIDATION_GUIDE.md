# CSS Consolidation Guide

## ✅ Completed
1. **Updated static/css/main.css** with comprehensive styles including:
   - All form styles
   - User info & logout button
   - Action cards
   - Timeline components
   - Tab system
   - Calendar (full implementation)
   - Modal system
   - Disponibilidade items
   - All utility classes

## 📋 Files That Need Template Updates

### High Priority - Core Patient Pages (3 files)
These are the most visible and should be updated first:

#### 1. `templates/core/patient_home.html`
- **Action**: Remove `<style>` block (lines 7-43)
- **Add**: `{% load static %}` at top
- **Add**: `<link rel="stylesheet" href="{% static 'css/main.css' %}">`
- **Status**: ⏳ Needs update

#### 2. `templates/core/patient_consultas.html`
- **Action**: Remove entire `<style>` block
- **Add**: Link to main.css
- **Status**: ⏳ Needs update

#### 3. `templates/core/patient_agendar.html`
- **Action**: Remove `<style>` block
- **Add**: Link to main.css
- **Status**: ⏳ Needs update

#### 4. `templates/core/patient_faturas.html`
- **Action**: Remove `<style>` block
- **Add**: Link to main.css  
- **Status**: ⏳ Needs update

###  High Priority - Médico Pages (4 files)

#### 5. `templates/medico/dashboard.html`
- **Action**: Remove inline styles
- **Add**: Link to main.css
- **Status**: ⏳ Needs update

#### 6. `templates/medico/agenda.html`
- **Action**: Remove massive style block (400+ lines)
- **Add**: Link to main.css
- **Note**: All calendar, tab, and modal styles are now in main.css
- **Status**: ⏳ Needs update

#### 7. `templates/medico/disponibilidade.html`
- **Action**: Remove inline styles or DELETE FILE (merged into agenda)
- **Status**: ⚠️ Redundant - can be removed

#### 8. `templates/medico/indisponibilidade.html`
- **Action**: Remove inline styles or DELETE FILE (merged into agenda)
- **Status**: ⚠️ Redundant - can be removed

### Medium Priority - Admin Pages (~15 files)

#### 9. `templates/admin/dashboard.html`
- **Action**: Remove inline styles
- **Add**: Link to main.css
- **Status**: ⏳ Needs update

#### 10. `templates/admin/consultas.html`
- **Action**: Remove style block
- **Add**: Link to main.css
- **Status**: ⏳ Needs update

#### 11. `templates/admin/consulta_form.html`
- **Action**: Remove style block
- **Add**: Link to main.css
- **Status**: ⏳ Needs update

#### 12-20. Other Admin Templates
All other admin templates (especialidades, unidades, regioes, utilizadores, faturas, etc.) follow the same pattern:
- Remove `<style>` blocks
- Add main.css link
- **Status**: ⏳ Needs batch update

### Low Priority - Already Using main.css but have duplicates (9 files)

These files already load main.css but ALSO have inline styles:

#### 21-25. Enfermeiro Templates
- `templates/enfermeiro/dashboard.html`
- `templates/enfermeiro/consultas.html`
- `templates/enfermeiro/pacientes.html`
- `templates/enfermeiro/relatorios.html`
- `templates/enfermeiro/paciente_detalhes.html`
- **Action**: Just remove the `<style>` blocks (they already have the link)
- **Status**: ⏳ Need cleanup

#### 26-28. Médico Detail Pages
- `templates/medico/detalhes_consulta.html`
- `templates/medico/registar_consulta.html`
- `templates/medico/recusar_consulta.html`
- **Action**: Just remove the `<style>` blocks
- **Status**: ⏳ Need cleanup

### Other Files

#### 29-30. Patient Utility Pages
- `templates/core/patient_perfil.html`
- `templates/core/patient_reagendar.html`
- **Action**: Keep as-is (already use main.css correctly)
- **Status**: ✅ Already good

## 📊 Impact Summary

| Category | Files | Total Lines of CSS to Remove | Status |
|----------|-------|------------------------------|--------|
| Patient Core | 4 | ~600 lines | ⏳ Pending |
| Médico Main | 4 | ~1,200 lines | ⏳ Pending |
| Admin | 15 | ~2,500 lines | ⏳ Pending |
| Enfermeiro | 5 | ~400 lines | ⏳ Pending |
| Already Good | 2 | 0 | ✅ Done |
| **TOTAL** | **30** | **~4,700 lines** | **3% Complete** |

## 🎯 Next Steps

### Immediate Actions Needed:
1. Update top 4 patient pages (most visible to users)
2. Update médico/agenda.html (largest single file impact)
3. Batch update all admin pages
4. Clean up enfermeiro pages
5. Delete redundant disponibilidade/indisponibilidade templates

### Template Pattern for Updates:

**Before:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
    <style>
        /* 200+ lines of CSS */
    </style>
</head>
```

**After:**
```html
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <title>Page Title</title>
    <link rel="stylesheet" href="{% static 'css/main.css' %}">
</head>
```

## ✨ Benefits Once Complete

1. **Performance**: 
   - Browser caching of CSS (loads once, cached forever)
   - Reduced HTML size by ~4,700 lines
   - Faster page loads

2. **Maintainability**:
   - Single source of truth for styles
   - Change button color once instead of 30 times
   - Consistent design language automatically

3. **Developer Experience**:
   - No more searching through 30 files to update a style
   - Easy to add new pages with consistent styling
   - Clear separation of concerns (HTML vs CSS)

4. **File Size Reduction**:
   - Each HTML file becomes 50-80% smaller
   - Total codebase reduction: ~4,700 lines of duplicate CSS

## 🔧 Testing Checklist

After each file update:
- [ ] Page loads without errors
- [ ] All elements are visible
- [ ] Buttons still work
- [ ] Forms are styled correctly
- [ ] Responsive design works
- [ ] No console errors

## 📝 Notes

- The main.css file now contains ALL styles needed for the entire application
- CSS variables ensure consistent theming across all pages
- All component styles (buttons, forms, tables, cards, etc.) are centralized
- Mobile responsive styles are included
- Print styles are included
