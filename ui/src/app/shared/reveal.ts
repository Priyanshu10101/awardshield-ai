import { Directive, ElementRef, OnDestroy, OnInit, inject } from '@angular/core';

/** Adds `.in` when the element scrolls into view (IntersectionObserver, once).
Pair with class="reveal". */
@Directive({ selector: '[appReveal]' })
export class Reveal implements OnInit, OnDestroy {
  private el = inject(ElementRef<HTMLElement>);
  private io?: IntersectionObserver;
  ngOnInit(): void {
    const node = this.el.nativeElement;
    if (typeof IntersectionObserver === 'undefined') { node.classList.add('in');
    return; }
    this.io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) { node.classList.add('in'); this.io?.disconnect(); }
    }), { threshold: 0.15 });
    this.io.observe(node);
  }
  ngOnDestroy(): void { this.io?.disconnect(); }
}
