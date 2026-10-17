import { Injectable, signal } from '@angular/core';

/** True while the landing page's big centred logo is on screen: the top bar then hides its small one. */
@Injectable({ providedIn: 'root' })
export class BrandState {
  readonly heroBrandVisible = signal(false);
}
