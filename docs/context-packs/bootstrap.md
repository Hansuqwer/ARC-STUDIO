# Bootstrap Context Pack

Generated during initial research phase.

## Theia Extension Pattern (verified from source)

Source: https://theia-ide.org/docs/widgets/

```ts
// Widget + ViewContribution pattern (verified against Theia 1.71)
@injectable()
export class MyWidget extends ReactWidget {
  static readonly ID = 'my:widget';
  static readonly LABEL = 'My Widget';

  @postConstruct()
  protected override init(): void {
    super.init();
    this.id = MyWidget.ID;
    this.title.label = MyWidget.LABEL;
  }

  protected render(): React.ReactNode {
    return <div>Hello World</div>;
  }
}

// theiaExtensions in package.json:
// { "frontend": "lib/browser/my-frontend-module" }
```

## Theia Product Branding (verified from source)

Source: https://theia-ide.org/docs/blueprint_documentation/

```json
// applications/browser/package.json
{
  "theia": {
    "frontend": {
      "config": {
        "applicationName": "My Product Name"
      }
    }
  }
}
```

## ARC Protocol Envelope (design decision)

All Python → TypeScript communication uses this envelope.
See: docs/DECISIONS/ADR-0002-python-daemon-json-boundary.md

## AG-UI Event Mapping

Source: https://docs.ag-ui.com/concepts/events

Key event types:
- RunStarted, RunFinished, RunError
- StepStarted, StepFinished, StepError  
- TextMessageStart, TextMessageContent, TextMessageEnd
- ToolCallStart, ToolCallArgs, ToolCallEnd
- StateSnapshot

## Context7 Library IDs (verified)

- Eclipse Theia: `/eclipse-theia/theia`
- LangGraph: `/langchain-ai/langgraph`
- Pydantic: `/pydantic/pydantic`
- Textual: `/Textualize/textual`
