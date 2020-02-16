"use strict";

let ws = new WebSocket('ws://localhost:8765');

let portfolios_subscribed = new Set();

ws.onopen = function(event){
    if (portfolios_subscribed.size > 0){
        ws.send("SET " + Array.from(portfolios_subscribed).join(' ')); 
    }
  };

let table_holder = document.getElementById('table_holder')
let table_content_holder = document.getElementById('tabla');
let table_content_basic_backup = table_content_holder.cloneNode(true);

ws.onmessage = function(event){
    let msg = JSON.parse(event.data);    

    for (let portfolio_id in msg) {
        for (let reco_id in msg[portfolio_id]) {

            let row = document.createElement('tr');
            let portfolio_cell = document.createElement('td');
            portfolio_cell.innerText = portfolio_id;
        
            let reco_cell = document.createElement('td');
            reco_cell.innerText = reco_id;
        
            let assets_cell = document.createElement('td');
            assets_cell.innerText = msg[portfolio_id][reco_id]['assets'];
        
            row.appendChild(portfolio_cell);
            row.appendChild(reco_cell);
            row.appendChild(assets_cell);
        
            table_content_holder.appendChild(row);
        }
    }
}

let all_button = document.getElementById('all');
let active_button = all_button;
let internas_button = document.getElementById('internas');
let externas_button = document.getElementById('externas');
let portfolio_button = document.getElementById('portfolio');
let portfolio_input = document.getElementById('portfolio_id_input');

function reset_table(){
    table_holder.removeChild(table_content_holder);
    table_content_holder = table_content_basic_backup.cloneNode(true);
    table_holder.appendChild(table_content_holder);
}

all_button.onclick = function(event){
    if (all_button == active_button)
    {
        return null;
    }

    active_button.classList.remove('activo');

    active_button = all_button;
    all_button.classList.add('activo');

    reset_table();

    ws.send('all');
}

internas_button.onclick = function(event){
    if (internas_button == active_button)
    {
        return null;
    }

    active_button.classList.remove('activo');

    active_button = internas_button;
    internas_button.classList.add('activo');

    reset_table();

    ws.send('internas');
}

externas_button.onclick = function(event){
    if (externas_button == active_button)
    {
        return null;
    }

    active_button.classList.remove('activo');

    active_button = externas_button;
    externas_button.classList.add('activo');

    reset_table();

    ws.send('externas');
}

let active_portfolio = null;

portfolio_button.onclick = function(event){
    let portfolio_id = portfolio_input.value;

    if (portfolio_button == active_button && portfolio_id != null && portfolio_id == active_portfolio)
    {
        return null;
    }    

    active_button.classList.remove('activo');
    
    active_button = portfolio_button;
    portfolio_button.classList.add('activo');

    reset_table();

    ws.send(portfolio_id);
}