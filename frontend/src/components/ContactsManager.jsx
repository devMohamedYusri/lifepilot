import { useState, useEffect } from 'react';
import { contactsApi } from '../api/client';

/**
 * Personal CRM - Contacts Manager
 */
export default function ContactsManager() {
    const [contacts, setContacts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState('all');
    const [needsAttention, setNeedsAttention] = useState({ overdue_contacts: [], upcoming_dates: [] });
    const [stats, setStats] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [selectedContact, setSelectedContact] = useState(null);
    const [showInteractionModal, setShowInteractionModal] = useState(null);

    useEffect(() => {
        fetchContacts();
        fetchNeedsAttention();
        fetchStats();
    }, [filter]);

    const fetchContacts = async () => {
        try {
            const params = {};
            if (filter !== 'all') params.relationship_type = filter;
            if (search) params.search = search;
            const data = await contactsApi.list(params);
            setContacts(data);
        } catch (err) {
            console.error('Failed to fetch contacts:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchNeedsAttention = async () => {
        try {
            const data = await contactsApi.needsAttention();
            setNeedsAttention(data);
        } catch (err) {
            console.error('Failed to fetch needs attention:', err);
        }
    };

    const fetchStats = async () => {
        try {
            const data = await contactsApi.stats();
            setStats(data);
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
    };

    const handleSearch = (e) => {
        e.preventDefault();
        fetchContacts();
    };

    const handleAddContact = async (contactData) => {
        try {
            await contactsApi.create(contactData);
            setShowAddModal(false);
            fetchContacts();
            fetchStats();
        } catch (err) {
            console.error('Failed to create contact:', err);
        }
    };

    const handleLogInteraction = async (contactId, interactionData) => {
        try {
            await contactsApi.logInteraction(contactId, interactionData);
            setShowInteractionModal(null);
            fetchContacts();
            fetchNeedsAttention();
        } catch (err) {
            console.error('Failed to log interaction:', err);
        }
    };

    const getTimeAgo = (dateStr) => {
        if (!dateStr) return 'Never';
        const date = new Date(dateStr);
        const now = new Date();
        const days = Math.floor((now - date) / (1000 * 60 * 60 * 24));
        if (days === 0) return 'Today';
        if (days === 1) return 'Yesterday';
        if (days < 7) return `${days} days ago`;
        if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
        return `${Math.floor(days / 30)} months ago`;
    };

    const getContactColor = (contact) => {
        if (!contact.next_contact_date) return 'text-surface-400';
        const next = new Date(contact.next_contact_date);
        const now = new Date();
        const days = Math.floor((next - now) / (1000 * 60 * 60 * 24));
        if (days < 0) return 'text-red-400';
        if (days < 7) return 'text-amber-400';
        return 'text-emerald-400';
    };

    const relationshipTypes = [
        { value: 'all', label: 'All' },
        { value: 'family', label: '👨‍👩‍👧 Family' },
        { value: 'friend', label: '🤝 Friends' },
        { value: 'colleague', label: '💼 Colleagues' },
        { value: 'professional', label: '🏢 Professional' },
        { value: 'mentor', label: '🎓 Mentors' },
        { value: 'acquaintance', label: '👋 Acquaintances' },
    ];

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="flex items-center gap-3 text-primary-400">
                    <div className="spinner"></div>
                    <span>Loading contacts...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white">👥 People</h2>
                    <p className="text-surface-300">Manage your relationships and stay connected</p>
                </div>
                <button onClick={() => setShowAddModal(true)} className="btn-primary">
                    + Add Contact
                </button>
            </div>

            {/* Stats Bar */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="glass rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-primary-400">{stats.total_contacts || 0}</div>
                        <div className="text-surface-300 text-sm">Total Contacts</div>
                    </div>
                    <div className="glass rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-emerald-400">{stats.interactions_this_week || 0}</div>
                        <div className="text-surface-300 text-sm">This Week</div>
                    </div>
                    <div className="glass rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-amber-400">{needsAttention.total_needing_attention || 0}</div>
                        <div className="text-surface-300 text-sm">Need Attention</div>
                    </div>
                    <div className="glass rounded-xl p-4 text-center">
                        <div className="text-2xl font-bold text-blue-400">{needsAttention.upcoming_dates?.length || 0}</div>
                        <div className="text-surface-300 text-sm">Upcoming Dates</div>
                    </div>
                </div>
            )}

            {/* Search & Filters */}
            <div className="flex flex-col md:flex-row gap-4">
                <form onSubmit={handleSearch} className="flex-1">
                    <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search contacts..."
                        className="w-full px-4 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                    />
                </form>
                <div className="flex gap-2 flex-wrap">
                    {relationshipTypes.map(type => (
                        <button
                            key={type.value}
                            onClick={() => setFilter(type.value)}
                            className={`px-3 py-1.5 rounded-lg text-sm transition-all ${filter === type.value
                                    ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                    : 'text-surface-300 hover:bg-white/5'
                                }`}
                        >
                            {type.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Contacts Grid */}
                <div className="lg:col-span-3">
                    {contacts.length === 0 ? (
                        <div className="glass rounded-xl p-12 text-center">
                            <div className="text-5xl mb-4">👥</div>
                            <h3 className="text-xl font-semibold text-white mb-2">No Contacts Yet</h3>
                            <p className="text-surface-300 mb-6">Add your first contact to start building your personal CRM.</p>
                            <button onClick={() => setShowAddModal(true)} className="btn-primary">+ Add Contact</button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {contacts.map(contact => (
                                <div
                                    key={contact.id}
                                    className="glass rounded-xl p-4 hover:bg-white/5 cursor-pointer transition-all"
                                    onClick={() => setSelectedContact(contact)}
                                >
                                    <div className="flex items-start gap-4">
                                        {/* Avatar */}
                                        <div className="w-12 h-12 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 font-bold text-lg">
                                            {contact.name?.charAt(0).toUpperCase() || '?'}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <h3 className="text-white font-medium truncate">{contact.name}</h3>
                                                <span className={`badge text-xs ${contact.relationship_type === 'family' ? 'bg-pink-500/20 text-pink-400' :
                                                        contact.relationship_type === 'friend' ? 'bg-green-500/20 text-green-400' :
                                                            contact.relationship_type === 'colleague' ? 'bg-blue-500/20 text-blue-400' :
                                                                'bg-surface-500/30 text-surface-300'
                                                    }`}>
                                                    {contact.relationship_type}
                                                </span>
                                            </div>
                                            {contact.company && (
                                                <p className="text-surface-400 text-sm">{contact.role ? `${contact.role} at ` : ''}{contact.company}</p>
                                            )}
                                            <div className={`text-sm mt-1 ${getContactColor(contact)}`}>
                                                Last: {getTimeAgo(contact.last_contact_date)}
                                            </div>
                                        </div>
                                        {/* Quick Actions */}
                                        <div className="flex gap-1">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); setShowInteractionModal({ contact, type: 'call' }); }}
                                                className="p-2 hover:bg-white/10 rounded-lg"
                                                title="Log Call"
                                            >📞</button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); setShowInteractionModal({ contact, type: 'message' }); }}
                                                className="p-2 hover:bg-white/10 rounded-lg"
                                                title="Log Message"
                                            >💬</button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Needs Attention Sidebar */}
                <div className="space-y-4">
                    <div className="glass rounded-xl p-4">
                        <h3 className="text-white font-semibold mb-3">⚠️ Needs Attention</h3>
                        {needsAttention.overdue_contacts?.length > 0 ? (
                            <div className="space-y-2">
                                {needsAttention.overdue_contacts.slice(0, 5).map(c => (
                                    <div key={c.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5">
                                        <span className="text-surface-200 text-sm truncate">{c.name}</span>
                                        <button
                                            onClick={() => setShowInteractionModal({ contact: c, type: 'message' })}
                                            className="text-primary-400 text-xs"
                                        >Log</button>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-surface-400 text-sm">All caught up! 🎉</p>
                        )}
                    </div>

                    {needsAttention.upcoming_dates?.length > 0 && (
                        <div className="glass rounded-xl p-4">
                            <h3 className="text-white font-semibold mb-3">🎂 Upcoming</h3>
                            <div className="space-y-2">
                                {needsAttention.upcoming_dates.slice(0, 5).map((item, i) => (
                                    <div key={i} className="flex items-center justify-between p-2 rounded-lg">
                                        <span className="text-surface-200 text-sm">{item.name}</span>
                                        <span className="text-amber-400 text-xs">{item.days_until}d</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Add Contact Modal */}
            {showAddModal && (
                <AddContactModal
                    onClose={() => setShowAddModal(false)}
                    onSave={handleAddContact}
                />
            )}

            {/* Contact Detail Modal */}
            {selectedContact && (
                <ContactDetailModal
                    contact={selectedContact}
                    onClose={() => setSelectedContact(null)}
                    onLogInteraction={(type) => setShowInteractionModal({ contact: selectedContact, type })}
                    onUpdate={() => { fetchContacts(); setSelectedContact(null); }}
                />
            )}

            {/* Interaction Logger Modal */}
            {showInteractionModal && (
                <InteractionLoggerModal
                    contact={showInteractionModal.contact}
                    defaultType={showInteractionModal.type}
                    onClose={() => setShowInteractionModal(null)}
                    onSave={(data) => handleLogInteraction(showInteractionModal.contact.id, data)}
                />
            )}
        </div>
    );
}

/**
 * Add Contact Modal
 */
function AddContactModal({ onClose, onSave }) {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        phone: '',
        company: '',
        role: '',
        relationship_type: '',
        how_met: '',
        birthday: '',
        notes: ''
    });
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!formData.name.trim()) return;
        setSaving(true);
        await onSave(formData);
        setSaving(false);
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="glass rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-white">Add Contact</h2>
                    <button onClick={onClose} className="text-surface-400 hover:text-white">✕</button>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="text-surface-300 text-sm block mb-1">Name *</label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                            className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            required
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-surface-300 text-sm block mb-1">Email</label>
                            <input
                                type="email"
                                value={formData.email}
                                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                                className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            />
                        </div>
                        <div>
                            <label className="text-surface-300 text-sm block mb-1">Phone</label>
                            <input
                                type="tel"
                                value={formData.phone}
                                onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                                className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-surface-300 text-sm block mb-1">Company</label>
                            <input
                                type="text"
                                value={formData.company}
                                onChange={(e) => setFormData(prev => ({ ...prev, company: e.target.value }))}
                                className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            />
                        </div>
                        <div>
                            <label className="text-surface-300 text-sm block mb-1">Role</label>
                            <input
                                type="text"
                                value={formData.role}
                                onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value }))}
                                className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="text-surface-300 text-sm block mb-1">How did you meet?</label>
                        <input
                            type="text"
                            value={formData.how_met}
                            onChange={(e) => setFormData(prev => ({ ...prev, how_met: e.target.value }))}
                            placeholder="e.g., Conference, mutual friend, work..."
                            className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                        />
                    </div>
                    <div>
                        <label className="text-surface-300 text-sm block mb-1">Birthday (MM-DD)</label>
                        <input
                            type="text"
                            value={formData.birthday}
                            onChange={(e) => setFormData(prev => ({ ...prev, birthday: e.target.value }))}
                            placeholder="e.g., 01-15"
                            className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                        />
                    </div>
                    <div>
                        <label className="text-surface-300 text-sm block mb-1">Notes</label>
                        <textarea
                            value={formData.notes}
                            onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                            className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            rows={3}
                        />
                    </div>
                    <p className="text-surface-400 text-xs">AI will suggest relationship type and contact frequency based on the info provided.</p>
                    <div className="flex gap-3 pt-4">
                        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 text-surface-300 hover:bg-white/5 rounded-lg">Cancel</button>
                        <button type="submit" disabled={saving} className="flex-1 btn-primary">
                            {saving ? 'Saving...' : 'Add Contact'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

/**
 * Contact Detail Modal
 */
function ContactDetailModal({ contact, onClose, onLogInteraction, onUpdate }) {
    const [interactions, setInteractions] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchInteractions();
    }, [contact.id]);

    const fetchInteractions = async () => {
        try {
            const data = await contactsApi.getInteractions(contact.id);
            setInteractions(data);
        } catch (err) {
            console.error('Failed to fetch interactions:', err);
        } finally {
            setLoading(false);
        }
    };

    const interactionIcon = {
        call: '📞',
        message: '💬',
        email: '📧',
        meeting: '☕',
        social: '🎉',
        gift: '🎁',
        other: '📝'
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="glass rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 font-bold text-2xl">
                            {contact.name?.charAt(0).toUpperCase() || '?'}
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white">{contact.name}</h2>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="badge bg-primary-500/20 text-primary-400">{contact.relationship_type}</span>
                                {contact.company && <span className="text-surface-400 text-sm">{contact.company}</span>}
                            </div>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-surface-400 hover:text-white text-xl">✕</button>
                </div>

                {/* Contact Info */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                    {contact.email && (
                        <div className="glass rounded-lg p-3">
                            <div className="text-surface-400 text-xs mb-1">Email</div>
                            <div className="text-white text-sm">{contact.email}</div>
                        </div>
                    )}
                    {contact.phone && (
                        <div className="glass rounded-lg p-3">
                            <div className="text-surface-400 text-xs mb-1">Phone</div>
                            <div className="text-white text-sm">{contact.phone}</div>
                        </div>
                    )}
                    {contact.birthday && (
                        <div className="glass rounded-lg p-3">
                            <div className="text-surface-400 text-xs mb-1">Birthday</div>
                            <div className="text-white text-sm">{contact.birthday}</div>
                        </div>
                    )}
                    {contact.how_met && (
                        <div className="glass rounded-lg p-3">
                            <div className="text-surface-400 text-xs mb-1">How Met</div>
                            <div className="text-white text-sm">{contact.how_met}</div>
                        </div>
                    )}
                </div>

                {/* Quick Actions */}
                <div className="flex gap-2 mb-6">
                    <button onClick={() => onLogInteraction('call')} className="btn-primary">📞 Log Call</button>
                    <button onClick={() => onLogInteraction('message')} className="px-4 py-2 glass rounded-lg text-white hover:bg-white/10">💬 Log Message</button>
                    <button onClick={() => onLogInteraction('meeting')} className="px-4 py-2 glass rounded-lg text-white hover:bg-white/10">☕ Log Meeting</button>
                </div>

                {/* Notes */}
                {contact.notes && (
                    <div className="glass rounded-lg p-4 mb-6">
                        <div className="text-surface-400 text-xs mb-2">Notes</div>
                        <p className="text-surface-200 text-sm">{contact.notes}</p>
                    </div>
                )}

                {/* Interaction History */}
                <div>
                    <h3 className="text-white font-semibold mb-3">📅 Interaction History</h3>
                    {loading ? (
                        <p className="text-surface-400 text-sm">Loading...</p>
                    ) : interactions.length === 0 ? (
                        <p className="text-surface-400 text-sm">No interactions logged yet.</p>
                    ) : (
                        <div className="space-y-3">
                            {interactions.map(i => (
                                <div key={i.id} className="glass rounded-lg p-3">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-white">{interactionIcon[i.type] || '📝'} {i.type}</span>
                                        <span className="text-surface-400 text-sm">{new Date(i.date).toLocaleDateString()}</span>
                                    </div>
                                    {i.summary && <p className="text-surface-200 text-sm">{i.summary}</p>}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

/**
 * Interaction Logger Modal
 */
function InteractionLoggerModal({ contact, defaultType, onClose, onSave }) {
    const [formData, setFormData] = useState({
        type: defaultType || 'message',
        date: new Date().toISOString().split('T')[0],
        summary: '',
        duration_minutes: '',
        mood: 'good',
        highlights: [],
        follow_ups: []
    });
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        await onSave(formData);
        setSaving(false);
    };

    const interactionTypes = [
        { value: 'call', label: '📞 Call' },
        { value: 'message', label: '💬 Message' },
        { value: 'email', label: '📧 Email' },
        { value: 'meeting', label: '☕ Meeting' },
        { value: 'social', label: '🎉 Social' },
        { value: 'gift', label: '🎁 Gift' },
    ];

    const moods = [
        { value: 'great', label: '😄 Great' },
        { value: 'good', label: '🙂 Good' },
        { value: 'neutral', label: '😐 Neutral' },
        { value: 'difficult', label: '😓 Difficult' },
    ];

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="glass rounded-2xl p-6 max-w-md w-full">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-white">Log Interaction with {contact.name}</h2>
                    <button onClick={onClose} className="text-surface-400 hover:text-white">✕</button>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Type Selector */}
                    <div className="flex flex-wrap gap-2">
                        {interactionTypes.map(type => (
                            <button
                                key={type.value}
                                type="button"
                                onClick={() => setFormData(prev => ({ ...prev, type: type.value }))}
                                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${formData.type === type.value
                                        ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                        : 'glass text-surface-300 hover:bg-white/5'
                                    }`}
                            >
                                {type.label}
                            </button>
                        ))}
                    </div>

                    <div>
                        <label className="text-surface-300 text-sm block mb-1">Date</label>
                        <input
                            type="date"
                            value={formData.date}
                            onChange={(e) => setFormData(prev => ({ ...prev, date: e.target.value }))}
                            className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                        />
                    </div>

                    <div>
                        <label className="text-surface-300 text-sm block mb-1">Summary</label>
                        <textarea
                            value={formData.summary}
                            onChange={(e) => setFormData(prev => ({ ...prev, summary: e.target.value }))}
                            placeholder="What did you talk about?"
                            className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                            rows={3}
                        />
                    </div>

                    <div>
                        <label className="text-surface-300 text-sm block mb-1">Duration (minutes)</label>
                        <input
                            type="number"
                            value={formData.duration_minutes}
                            onChange={(e) => setFormData(prev => ({ ...prev, duration_minutes: parseInt(e.target.value) || '' }))}
                            className="w-full px-3 py-2 bg-surface-800 border border-surface-600 rounded-lg text-white"
                        />
                    </div>

                    <div>
                        <label className="text-surface-300 text-sm block mb-2">How did it go?</label>
                        <div className="flex gap-2">
                            {moods.map(mood => (
                                <button
                                    key={mood.value}
                                    type="button"
                                    onClick={() => setFormData(prev => ({ ...prev, mood: mood.value }))}
                                    className={`px-3 py-1.5 rounded-lg text-sm ${formData.mood === mood.value
                                            ? 'bg-primary-500/20 text-primary-400'
                                            : 'glass text-surface-300'
                                        }`}
                                >
                                    {mood.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="flex gap-3 pt-4">
                        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 text-surface-300 hover:bg-white/5 rounded-lg">Cancel</button>
                        <button type="submit" disabled={saving} className="flex-1 btn-primary">
                            {saving ? 'Saving...' : 'Log Interaction'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
