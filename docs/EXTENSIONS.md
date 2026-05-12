# ARC Studio — Extension Guide

## Theia Extension vs VS Code Plugin

ARC Studio uses **native Theia extensions** (compiled into the app) not VS Code plugins.

- Native extensions: full access to Theia APIs, DI container, backend services
- VS Code plugins: limited to VS Code extension API surface via `plugin-ext`

All 9 ARC extensions are native Theia extensions loaded at build time.

## Extension Anatomy

```
theia-extensions/arc-myext/
├── package.json          ← declares theiaExtensions entry points
├── tsconfig.json         ← extends ../../tsconfig.base.json
└── src/
    ├── browser/
    │   ├── arc-myext-frontend-module.ts   ← ContainerModule
    │   ├── arc-myext-widget.tsx           ← ReactWidget
    │   └── arc-myext-contribution.ts      ← AbstractViewContribution
    └── node/
        └── arc-myext-backend-module.ts    ← backend ContainerModule
```

## Key Theia APIs (verified against 1.71)

### Commands
```ts
bind(CommandContribution).toService(MyContribution);
// registerCommands(registry: CommandRegistry) { registry.registerCommand(...) }
```

### Widgets
```ts
export class MyWidget extends ReactWidget {
  static readonly ID = 'my:widget';
  protected render(): React.ReactNode { return <div>...</div>; }
}
```

### View Contributions (Activity Bar)
```ts
export class MyContribution extends AbstractViewContribution<MyWidget> {
  constructor() {
    super({ widgetId: MyWidget.ID, widgetName: 'My Widget',
            defaultWidgetOptions: { area: 'left' }, toggleCommandId: 'my:open' });
  }
}
```

### Preferences
```ts
bind(PreferenceContribution).toConstantValue({ schema: MySchema });
```

### Backend ↔ Frontend IPC
```ts
// Backend: ConnectionHandler + JsonRpcConnectionHandler
// Frontend: WebSocketConnectionProvider.createProxy(SERVICE_PATH)
```

## Sources

- https://theia-ide.org/docs/widgets/
- https://theia-ide.org/docs/extensions/
- https://theia-ide.org/docs/preferences/
- https://github.com/eclipse-theia/theia-ide (reference implementation)
