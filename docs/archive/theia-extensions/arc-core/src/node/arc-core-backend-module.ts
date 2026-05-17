/**
 * ARC Core — Backend Module
 *
 * Registers the ARC service on the Theia backend (Node.js process).
 * Source: https://theia-ide.org/docs/extensions/ (backend services)
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { ConnectionHandler, JsonRpcConnectionHandler } from '@theia/core/lib/common/messaging';
import { ArcServiceSymbol, ARC_SERVICE_PATH } from '../common/arc-protocol';
import { ArcServiceImpl } from './arc-service-impl';

export default new ContainerModule(bind => {
  bind(ArcServiceImpl).toSelf().inSingletonScope();
  bind(ArcServiceSymbol).toService(ArcServiceImpl);

  bind(ConnectionHandler).toDynamicValue(ctx =>
    new JsonRpcConnectionHandler(ARC_SERVICE_PATH, () =>
      ctx.container.get<ArcServiceImpl>(ArcServiceImpl)
    )
  ).inSingletonScope();
});
