import { runWithConcurrency } from './batch';

describe('runWithConcurrency', () => {
  it('never exceeds the configured concurrency and continues after handled failures', async () => {
    let active = 0;
    let maximum = 0;
    const completed: number[] = [];
    await runWithConcurrency([1, 2, 3, 4, 5], 3, async (item) => {
      active += 1;
      maximum = Math.max(maximum, active);
      await new Promise((resolve) => setTimeout(resolve, 2));
      completed.push(item);
      active -= 1;
    });
    expect(maximum).toBe(3);
    expect(completed).toHaveLength(5);
  });
});
