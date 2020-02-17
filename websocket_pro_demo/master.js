"use strict";

let ws = new WebSocket('ws://localhost:8765');

let portfolios_subscribed = new Set();

let table_holder = document.getElementById('table_holder')
let table_content_holder = document.getElementById('tabla');
let table_content_basic_backup = table_content_holder.cloneNode(true);

ws.onmessage = recv_msg;


function recv_msg(event){
    
    if (event.data == 'deploying'){
        console.log('el servicio se ha apagado porque esta desplegandose una nueva version. En breve se recuperará la conexion');

        ws.close();

        let interval = setInterval(function(){ 

            ws = new WebSocket('ws://localhost:8765');

            ws.onopen = function(event){
                if (portfolios_subscribed.size > 0){
                    clearInterval(interval);
                    reset_table();
                    ws.send("SET " + Array.from(portfolios_subscribed).join(' ')); 
                }
            };

            ws.onerror = function(){
                console.log('el servicio sigue desplegando');
            }

            ws.onmessage = recv_msg;

        }, 7000);
        
        
    } else {

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
}

let portfolio_button = document.getElementById('portfolio');
let portfolio_input = document.getElementById('portfolio_id_input');
let portfolios_holder = document.getElementById('topics_holder');

function reset_table(){
    table_holder.removeChild(table_content_holder);
    table_content_holder = table_content_basic_backup.cloneNode(true);
    table_holder.appendChild(table_content_holder);
}

portfolio_button.onclick = function(event){
    let portfolio_id = portfolio_input.value;

    if (portfolio_id != null && portfolios_subscribed.has(portfolio_id))
    {
        return null;
    }    

    reset_table();

    portfolios_subscribed.add(portfolio_id);

    let topic_holder = document.createElement('div');
    let portfolio_id_holder = document.createElement('div');
    let delete_topic = document.createElement('button');
    delete_topic.innerText = "X";

    portfolio_id_holder.innerText = portfolio_id;

    delete_topic.onclick = function(){
        portfolios_holder.removeChild(topic_holder);
        portfolios_subscribed.delete(portfolio_id);
        reset_table();
        ws.send('UNSET ' + portfolio_id);
    }

    topic_holder.appendChild(portfolio_id_holder);
    topic_holder.appendChild(delete_topic);

    portfolios_holder.appendChild(topic_holder);

    ws.send('SET ' + portfolio_id);
}