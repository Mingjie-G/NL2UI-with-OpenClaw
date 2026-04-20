import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

// 将我们之前定义的 JSON Schema 接口简单定义一下，方便 TS 推导
interface Schema {
  meta: { task_id: string; title: string; description: string };
  elements: any[];
  actions: any[];
}

@customElement('interactive-card')
export class InteractiveCard extends LitElement {
  // 接收外部传入的 JSON Schema
  @property({ type: Object }) schema!: Schema;

  // 内部状态：记录用户填写的表单数据
  @state() private formData: Record<string, string> = {};
  @state() private isSubmitted: boolean = false;

  // Lit 默认使用 Shadow DOM，因此这里的 CSS 只作用于组件内部，不会污染全局
  static styles = css`
    .card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; background: #fff; max-width: 400px; font-family: sans-serif; }
    .title { font-size: 1.125rem; font-weight: bold; margin-bottom: 4px; color: #1e293b; }
    .desc { font-size: 0.875rem; color: #64748b; margin-bottom: 16px; }
    .form-group { margin-bottom: 12px; }
    label { display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 4px; color: #334155; }
    input, select { width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; }
    input:focus, select:focus { outline: none; border-color: #3b82f6; }
    .actions { display: flex; gap: 8px; margin-top: 16px; }
    button { padding: 8px 16px; border: none; border-radius: 4px; font-size: 0.875rem; cursor: pointer; transition: background 0.2s; }
    .primary { background-color: #3b82f6; color: white; }
    .primary:hover { background-color: #2563eb; }
    .default { background-color: #f1f5f9; color: #334155; }
    .default:hover { background-color: #e2e8f0; }
  `;

  // 收集表单数据
  private _handleInput(id: string, e: Event) {
    const target = e.target as HTMLInputElement | HTMLSelectElement;
    this.formData = { ...this.formData, [id]: target.value };
  }

  // 点击按钮，向父组件抛出自定义事件
  private _handleAction(action: any) {
    if (this.isSubmitted) return;
    this.isSubmitted = true;

    // Web Components 传参的标准做法：派发 CustomEvent
    const event = new CustomEvent('ui-action', {
      detail: {
        task_id: this.schema.meta.task_id,
        action_type: action.action_type,
        data: this.formData
      },
      bubbles: true,
      composed: true // 极其重要：允许事件穿透 Shadow DOM 冒泡到外层
    });
    this.dispatchEvent(event);
  }

  render() {
    if (!this.schema || !this.schema.elements) return html``;

    return html`
      <div class="card">
        <div class="title">${this.schema.meta.title}</div>
        <div class="desc">${this.schema.meta.description}</div>

        <div class="elements">
          ${this.schema.elements.map(el => {
            if (el.type === 'text_display') {
              return html`<div style="font-weight: 500; margin-bottom: 8px;">${el.content}</div>`;
            }
            if (el.type === 'input') {
              return html`
                <div class="form-group">
                  <label>${el.label}</label>
                  <input type="text" placeholder="${el.placeholder || ''}" @input="${(e: Event) => this._handleInput(el.id, e)}" ?disabled=${this.isSubmitted}>
                </div>
              `;
            }
            if (el.type === 'select') {
              return html`
                <div class="form-group">
                  <label>${el.label}</label>
                  <select @change="${(e: Event) => this._handleInput(el.id, e)}" ?disabled=${this.isSubmitted}>
                    ${el.options?.map((opt: any) => html`
                      <option value="${opt.value}" ?selected=${opt.value === el.default_value}>${opt.label}</option>
                    `)}
                  </select>
                </div>
              `;
            }
            return html``;
          })}
        </div>

        <div class="actions">
          ${this.schema.actions?.map(action => html`
            <button class="${action.theme === 'primary' ? 'primary' : 'default'}" 
                    @click="${() => this._handleAction(action)}"
                    ?disabled=${this.isSubmitted}>
              ${this.isSubmitted && action.action_type === 'submit' ? '已提交 ✓' : action.label}
            </button>
          `)}
        </div>
      </div>
    `;
  }
}
