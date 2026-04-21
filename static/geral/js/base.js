function alternarBarraLateral(){
    
    const barraLateral = document.getElementById("barra-lateral")
    const icone = document.getElementById("icon-barra-lateral")
    const conteudoPrincipal = document.getElementById("conteudo-principal")

    if(barraLateral.className === "barra-lateral"){
        barraLateral.className = "barra-lateral-fechada";
        icone.textContent = "chevron_right";
        conteudoPrincipal.className = "conteudo-principal-fechado"

    }else {
        barraLateral.className = "barra-lateral";
        icone.textContent = "chevron_left";
        conteudoPrincipal.className = "conteudo-principal-aberto"
    }
}