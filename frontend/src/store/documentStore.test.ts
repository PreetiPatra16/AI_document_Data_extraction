import { useDocumentStore } from './documentStore';

describe('document store previews', () => {
  beforeEach(() => {
    localStorage.clear();
    useDocumentStore.setState({ items: [] });
  });

  it('stages files and revokes previews when removed', () => {
    const revoke = vi.spyOn(URL, 'revokeObjectURL');
    useDocumentStore.getState().stageFiles([new File(['x'], 'claim.png', { type: 'image/png' })]);
    const item = useDocumentStore.getState().items[0];
    expect(item.status).toBe('STAGED');
    useDocumentStore.getState().removeItem(item.localId);
    expect(revoke).toHaveBeenCalledWith('blob:preview');
  });
});
