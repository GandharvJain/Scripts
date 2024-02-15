#!/usr/bin/env node
const fs = require('fs').promises;
const path = require('path');
const process = require('process');
const {authenticate} = require('@google-cloud/local-auth');
const {google} = require('googleapis');

// If modifying these scopes, delete token.json.
const SCOPES = ['https://www.googleapis.com/auth/calendar.events'];
// The file token.json stores the user's access and refresh tokens, and is
// created automatically when the authorization flow completes for the first
// time.
const SECRETS_PATH = '/home/gandharv/Scripts/secrets/'
const TOKEN_PATH = SECRETS_PATH + 'google-calendar-token.json';
const CREDENTIALS_PATH = SECRETS_PATH + 'google-calendar-credentials.json';
const WHATSAPP_CONFIG_PATH = SECRETS_PATH + 'whatsapp_config.json';
const WHATSAPP_AUTH_PATH = SECRETS_PATH + '.wwebjs_auth';
const WHATSAPP_CACHE_PATH = SECRETS_PATH + '.wwebjs_cache';

const whatsappConfig = require(WHATSAPP_CONFIG_PATH);

/*
*	Reads previously authorized credentials from the save file.
*
*	@return {Promise<OAuth2Client|null>}
*/
async function loadSavedCredentialsIfExist() {
	try {
		const content = await fs.readFile(TOKEN_PATH);
		const credentials = JSON.parse(content);
		return google.auth.fromJSON(credentials);
	} catch (err) {
		return null;
	}
}

/*
*	Serializes credentials to a file compatible with GoogleAUth.fromJSON.
*
*	@param {OAuth2Client} client
*	@return {Promise<void>}
*/
async function saveCredentials(client) {
	const content = await fs.readFile(CREDENTIALS_PATH);
	const keys = JSON.parse(content);
	const key = keys.installed || keys.web;
	const payload = JSON.stringify({
		type: 'authorized_user',
		client_id: key.client_id,
		client_secret: key.client_secret,
		refresh_token: client.credentials.refresh_token,
	});
	await fs.writeFile(TOKEN_PATH, payload);
}

/*
*	Load or request or authorization to call APIs.
*
*/
async function authorize() {
	let client = await loadSavedCredentialsIfExist();
	if (client) {
		return client;
	}
	client = await authenticate({
		scopes: SCOPES,
		keyfilePath: CREDENTIALS_PATH,
	});
	if (client.credentials) {
		await saveCredentials(client);
	}
	return client;
}


const qrcode = require('qrcode-terminal');

const { Client, LocalAuth, LocalWebCache } = require('whatsapp-web.js');

const client = new Client({
	authStrategy: new LocalAuth({
		dataPath: WHATSAPP_AUTH_PATH
	}),
	webVersionCache: new LocalWebCache({
		path: WHATSAPP_CACHE_PATH
	}),
	puppeteer: {
		args: ['--no-sandbox'],
	}
});

client.on('qr', (qr) => {qrcode.generate(qr, { small: true });});

client.on('loading_screen', (percent, message) => {console.log('LOADING SCREEN', percent, message);});

client.on('authenticated', () => {console.log('AUTHENTICATED');});

client.on('auth_failure', msg => {console.error('AUTHENTICATION FAILURE', msg);});

client.on('ready', async () => {
	console.log('Client is ready!');
	// const allChats = await client.getChats();
	// for (const index in allChats) {
	// 	const chat = allChats[index];
	// 	if (chat.isGroup) {
	// 		console.log(chat.name);
	// 		console.log(chat.id._serialized);
	// 		console.log('------');
	// 	}
	// }
	// console.log("Finished on ready");
});

// Parse zoom meeting message
async function insertCalendarEvent(message, auth) {

	let lines = message.body.split('\n').filter(Boolean);
	
	let topic = lines[1].replace('Topic: ', '');

	let startTimeString = lines[2].replace('Time: ', '');
	let timeArray = /([A-Z][a-z]+) (\d+), (\d+) (\d+):(\d+) ([A-Z]+) (\w+)/.exec(startTimeString).slice(1, -1);
	let startTime = new Date(timeArray[1] + ' ' + timeArray[0] + ' ' + timeArray[2] + ' ' + timeArray[3] + ':' + timeArray[4] + ':00 ' + timeArray[5])

	let endTime = new Date(startTime.getTime());
	endTime.setHours(endTime.getHours() + 2);

	let description = lines.splice(3).join('\n');
	
	let event = {
		'summary': topic,
		'start': {'dateTime': startTime.toISOString()},
		'end': {'dateTime': endTime.toISOString()},
		'description': description
	}

	const calendar = google.calendar({version: 'v3', auth});
	calendar.events.insert({
		auth: auth,
		calendarId: whatsappConfig.calendarId,
		resource: event
	}).then(console.log).catch(console.error)
}

async function quickAddCalendarEvent(message, auth) {
	let text = message.body;
	text = text.replace('Join', 'Description: Join');
	// console.log({text});

	const calendar = google.calendar({version: 'v3', auth});
	calendar.events.quickAdd({
		auth: auth,
		calendarId: whatsappConfig.calendarId,
		text: text
	}).then(() => console.log("Successfully added event to calendar!")).catch(console.error)
}


client.on('message_create', async (message) => {
	const selfUserId = client.info.wid._serialized;
	if (message.from != selfUserId)
		return;
	console.log("SELF", message.author??message.from, message.body);

	if (message.to == whatsappConfig.groupId && message.body.startsWith(whatsappConfig.checkString)) {
		authorize()
		.then((auth) => quickAddCalendarEvent(message, auth))
		.catch(console.error);
	}
	// let chat = await message.getChat();
	// let messages = await chat.fetchMessages({limit: 10});
	// messages = messages.map(x => x.body);
	// console.log(messages);
});

client.on('message', async (message) => {
	console.log(message.author??message.from, message.body);

	if (message.from == whatsappConfig.groupId && message.body.startsWith(whatsappConfig.checkString)) {
		authorize()
			.then((auth) => quickAddCalendarEvent(message, auth))
			.catch(console.error);
	}
});

client.initialize();
