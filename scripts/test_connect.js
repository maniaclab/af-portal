#!/usr/bin/env node
// Standalone test: replicates connect.get_group_info('root.atlas-af', date_format='calendar')

const ENDPOINT = process.env.CONNECT_API_ENDPOINT;
const TOKEN = process.env.CONNECT_API_TOKEN;

if (!ENDPOINT || !TOKEN) {
  console.error('CONNECT_API_ENDPOINT and CONNECT_API_TOKEN env vars must be set');
  process.exit(1);
}

const NON_REMOVABLE = new Set([
  'root', 'root.atlas-af', 'root.atlas-af.staff', 'root.atlas-af.uchicago',
  'root.atlas-ml', 'root.atlas-ml.staff', 'root.iris-hep-ml', 'root.iris-hep-ml.staff',
  'root.osg', 'root.osg.login-nodes',
]);

// Replicates Python's strftime("%B %m %Y") — month name, zero-padded month number, year
function calendarDate(dateStr) {
  const d = new Date(dateStr);
  const name = d.toLocaleString('en-US', { month: 'long' });
  const num = String(d.getUTCMonth() + 1).padStart(2, '0');
  return `${name} ${num} ${d.getUTCFullYear()}`;
}

async function getGroupInfo(groupName, dateFormat = 'calendar') {
  const res = await fetch(`${ENDPOINT}/v1alpha1/groups/${groupName}?token=${TOKEN}`);
  const data = await res.json();
  if (data.kind === 'Error') throw new Error(data.message);
  if (data.kind !== 'Group') return null;

  const m = data.metadata;
  const group = {
    name: m.name,
    display_name: m.display_name,
    description: m.description,
    email: m.email,
    phone: m.phone,
    purpose: m.purpose,
    unix_id: m.unix_id,
    pending: m.pending,
    is_removable: !NON_REMOVABLE.has(groupName),
  };

  if (dateFormat === 'iso') {
    group.creation_date = new Date(m.creation_date).toISOString();
  } else if (dateFormat === 'calendar') {
    group.creation_date = calendarDate(m.creation_date);
  } else {
    group.creation_date = m.creation_date;
  }

  return group;
}

getGroupInfo('root.atlas-af', 'calendar')
  .then(info => console.log(JSON.stringify(info, null, 2)))
  .catch(err => { console.error(err.message); process.exit(1); });
